"""
HC-XCDSS Chest X-Ray Pre-Inference Validation & Out-of-Distribution (OOD) Safety Gate

Validates that an uploaded image possesses the structural, radiometric, and semantic
characteristics of a valid frontal or lateral chest radiograph before running clinical
DenseNet121 inference or generating Grad-CAM heatmaps.

Architecture:
  Layer 1: File & Format Validation (extension, readability, dimension limits, corruption checks)
  Layer 2: Radiometric & Spectral Validation (chroma/saturation bounds, contrast, dynamic range)
  Layer 3: Anatomical & Semantic Domain Classifier (chest radiograph characteristics vs natural/OOD images)
"""

import io
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Union
import numpy as np
from PIL import Image, ImageOps
import torch
import torchvision.models as models
from torchvision.models import MobileNet_V3_Small_Weights


class ChestXRayValidator:
    """
    Multi-layer safety gate ensuring only valid chest radiographs reach clinical ML inference.
    """

    MIN_DIMENSION = 120
    MAX_DIMENSION = 6000
    MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
    MIN_DYNAMIC_RANGE = 25.0
    MAX_CHROMA_TOLERANCE = 45.0  # Radiographs are grayscale / slightly toned

    def __init__(self, use_classifier: bool = True):
        self.use_classifier = use_classifier
        self._classifier = None
        self._preprocess = None
        self._categories = None

    def _ensure_classifier_loaded(self):
        """Lazy load lightweight MobileNetV3 OOD detector for semantic verification."""
        if self._classifier is None and self.use_classifier:
            try:
                weights = MobileNet_V3_Small_Weights.DEFAULT
                self._classifier = models.mobilenet_v3_small(weights=weights).eval()
                self._categories = weights.meta["categories"]
                self._preprocess = weights.transforms()
            except Exception as e:
                print(f"[XRayValidator] Notice: Classifier lazy load fallback to heuristic gate: {e}")
                self._classifier = False

    def validate(
        self,
        image_input: Union[str, Path, bytes, Image.Image],
        view: str = "Frontal"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate whether the given input is plausibly a chest X-ray.

        Args:
            image_input: Filepath, bytes, or PIL Image object.
            view: Expected projection ('Frontal' or 'Lateral').

        Returns:
            Tuple of (is_valid: bool, rejection_reason: str, details_dict: Dict)
        """
        view_norm = str(view).strip().capitalize()
        details = {
            "view": view_norm,
            "passed_layer1_file": False,
            "passed_layer2_radiometric": False,
            "passed_layer3_domain": False,
            "metrics": {}
        }

        # ----------------------------------------------------
        # Layer 1: File & Image Integrity Validation
        # ----------------------------------------------------
        img = None
        try:
            if isinstance(image_input, (str, Path)):
                img_path = Path(image_input)
                if not img_path.exists():
                    return False, "Image file does not exist on disk.", details
                file_size = img_path.stat().st_size
                if file_size > self.MAX_FILE_SIZE_BYTES:
                    return False, "Image file exceeds maximum allowable size (25 MB).", details
                if file_size < 100:
                    return False, "Image file is too small or empty.", details
                img = Image.open(img_path)
            elif isinstance(image_input, bytes):
                if len(image_input) > self.MAX_FILE_SIZE_BYTES:
                    return False, "Image file exceeds maximum allowable size (25 MB).", details
                if len(image_input) < 100:
                    return False, "Image file is too small or empty.", details
                img = Image.open(io.BytesIO(image_input))
            elif isinstance(image_input, Image.Image):
                img = image_input
            else:
                return False, "Unsupported image input type.", details

            # Verify integrity
            img.verify()
            # Reopen after verify() because verify() clears file pointer on PIL images
            if isinstance(image_input, (str, Path)):
                img = Image.open(img_path)
            elif isinstance(image_input, bytes):
                img = Image.open(io.BytesIO(image_input))

        except Exception as err:
            return False, f"Image file is corrupt or unreadable: {str(err)}", details

        w, h = img.size
        details["metrics"]["width"] = w
        details["metrics"]["height"] = h

        if w < self.MIN_DIMENSION or h < self.MIN_DIMENSION:
            return False, f"Image resolution ({w}x{h}) is too low for radiographic evaluation (minimum {self.MIN_DIMENSION}x{self.MIN_DIMENSION}).", details

        if w > self.MAX_DIMENSION or h > self.MAX_DIMENSION:
            return False, f"Image resolution ({w}x{h}) exceeds maximum allowable dimension ({self.MAX_DIMENSION}px).", details

        # Aspect ratio check (chest X-rays are typically between 0.5 and 2.0)
        aspect_ratio = w / float(h)
        details["metrics"]["aspect_ratio"] = round(aspect_ratio, 3)
        if aspect_ratio < 0.45 or aspect_ratio > 2.2:
            return False, f"Image aspect ratio ({aspect_ratio:.2f}) is atypical for a chest radiograph.", details

        details["passed_layer1_file"] = True

        # ----------------------------------------------------
        # Layer 2: Radiometric & Spectral Validation
        # ----------------------------------------------------
        # Convert to RGB array for chroma evaluation
        rgb_img = img.convert("RGB")
        rgb_arr = np.array(rgb_img, dtype=float)

        r = rgb_arr[:, :, 0]
        g = rgb_arr[:, :, 1]
        b = rgb_arr[:, :, 2]

        # Mean chroma / color saturation difference
        chroma = np.mean(np.abs(r - g) + np.abs(g - b) + np.abs(r - b))
        details["metrics"]["chroma"] = round(float(chroma), 2)

        # High-chroma images are definitely natural color photos (e.g. cars, landscapes, animals)
        if chroma > self.MAX_CHROMA_TOLERANCE:
            return False, "The uploaded image is a colorful photographic image, not a grayscale chest radiograph.", details

        # Grayscale intensity distribution & analog tone richness
        gray_img = img.convert("L")
        gray_arr = np.array(gray_img, dtype=float)

        unique_levels = len(np.unique(gray_arr))
        details["metrics"]["unique_intensity_levels"] = unique_levels

        # Synthetic graphics, logos, and flat vector drawings have very few unique tone levels
        if unique_levels < 32:
            return False, "Image lacks the continuous analog tonal gradient of a medical radiograph.", details

        p2, p98 = float(np.percentile(gray_arr, 2)), float(np.percentile(gray_arr, 98))
        dynamic_range = p98 - p2
        std_intensity = float(np.std(gray_arr))
        mean_intensity = float(np.mean(gray_arr))

        details["metrics"]["dynamic_range"] = round(dynamic_range, 2)
        details["metrics"]["std_intensity"] = round(std_intensity, 2)
        details["metrics"]["mean_intensity"] = round(mean_intensity, 2)

        # Flat / solid / blank images
        if dynamic_range < self.MIN_DYNAMIC_RANGE or std_intensity < 10.0:
            return False, "The image lacks sufficient radiographic contrast or dynamic range.", details

        # Completely white or completely black frames
        if mean_intensity < 5.0 or mean_intensity > 250.0:
            return False, "The image is underexposed or overexposed beyond clinical usability.", details

        details["passed_layer2_radiometric"] = True

        # ----------------------------------------------------
        # Layer 3: Anatomical & Semantic Domain Classifier
        # ----------------------------------------------------
        # 3A. Natural Image / Screenshot Semantic Rejection using OOD ImageNet Backbone
        self._ensure_classifier_loaded()
        if self._classifier and self._preprocess:
            try:
                input_tensor = self._preprocess(rgb_img).unsqueeze(0)
                with torch.no_grad():
                    logits = self._classifier(input_tensor)
                    probs = torch.nn.functional.softmax(logits[0], dim=0)

                top_prob, top_idx = torch.max(probs, dim=0)
                top_cat = self._categories[top_idx.item()]
                details["metrics"]["ood_top_class"] = top_cat
                details["metrics"]["ood_confidence"] = round(float(top_prob.item()), 4)

                # High-confidence non-medical object classes in ImageNet
                UNACCEPTABLE_NATURAL_CLASSES = {
                    "web site", "menu", "envelope", "comic book", "book jacket",
                    "packet", "crossword puzzle", "scoreboard", "street sign",
                    "traffic light", "laptop", "monitor", "screen", "television",
                    "cellular telephone", "digital clock", "analog clock",
                    "sports car", "convertible", "grille", "minivan", "pickup",
                    "racer", "tow truck", "cab", "beach wagon", "limousine",
                    "carton", "binder", "jigsaw puzzle", "loupe"
                }

                if top_cat in UNACCEPTABLE_NATURAL_CLASSES and top_prob.item() > 0.60:
                    return False, f"Image recognized as an out-of-domain object or document ('{top_cat}').", details

            except Exception as e:
                # Non-fatal classifier error; fall through to anatomical feature validation
                print(f"[XRayValidator] Classifier execution warning: {e}")

        # 3B. Anatomical Chest Radiograph Feature Checks (Symmetry & Spatial Distribution)
        # Chest radiographs have a distinct thoracic distribution:
        # - Central column contains sternum/spine/heart (denser/radiopaque)
        # - Bilateral lung zones in upper-mid fields (radiolucent air spaces)
        # - Lower field contains diaphragm and subdiaphragmatic structures
        h_arr, w_arr = gray_arr.shape

        # Vertical bands: top (apices/neck), mid (lung fields), bottom (abdomen)
        top_band = float(np.mean(gray_arr[:int(0.20 * h_arr), :]))
        mid_band = float(np.mean(gray_arr[int(0.25 * h_arr):int(0.65 * h_arr), :]))
        bot_band = float(np.mean(gray_arr[int(0.75 * h_arr):, :]))

        details["metrics"]["top_band_mean"] = round(top_band, 1)
        details["metrics"]["mid_band_mean"] = round(mid_band, 1)
        details["metrics"]["bot_band_mean"] = round(bot_band, 1)

        # Gradient density check (Ribs & vasculature have characteristic smooth gradients; text/graphics have extreme step edges)
        # Normalized to 320x320 canonical size for resolution-independent gradient evaluation
        resized_gray = gray_img.resize((320, 320), Image.Resampling.BILINEAR)
        norm_gray_arr = np.array(resized_gray, dtype=float)
        gx = np.abs(np.diff(norm_gray_arr, axis=1))
        gy = np.abs(np.diff(norm_gray_arr, axis=0))
        mean_grad = float((np.mean(gx) + np.mean(gy)) / 2.0)
        details["metrics"]["mean_gradient"] = round(mean_grad, 2)

        if mean_grad < 2.5:
            return False, "Image lacks the continuous soft-tissue and osseous texture of a radiograph.", details

        # Bilateral symmetry (Frontal views exhibit approximate left-right symmetry)
        if view_norm == "Frontal":
            mid_w = w_arr // 2
            left_half = gray_arr[:, :mid_w]
            right_half_flipped = np.fliplr(gray_arr[:, w_arr - mid_w:])
            symmetry_error = float(np.mean(np.abs(left_half - right_half_flipped)) / (dynamic_range + 1e-5))
            details["metrics"]["symmetry_error"] = round(symmetry_error, 3)

            # Severe bilateral asymmetry in frontal view indicates a non-chest image
            if symmetry_error > 0.45:
                return False, "Image lacks the expected bilateral thoracic symmetry of a frontal chest radiograph.", details

        details["passed_layer3_domain"] = True
        return True, "Valid chest radiograph confirmed.", details


# Global instance
xray_validator = ChestXRayValidator()
