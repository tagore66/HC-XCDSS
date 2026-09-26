import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image


PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.append(
    str(PROJECT_ROOT / "src" / "models")
)

from densenet import CheXpertDenseNet


# --------------------------------------------------
# Configuration
# --------------------------------------------------

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "models"
    / "checkpoints"
    / "densenet121_320_noaug_best.pth"
)


TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]


TRANSFORM = transforms.Compose([

    transforms.Resize(
        (320, 320)
    ),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[
            0.485,
            0.456,
            0.406
        ],

        std=[
            0.229,
            0.224,
            0.225
        ]
    )
])


# --------------------------------------------------
# Explainer
# --------------------------------------------------

class XRayExplainer:

    def __init__(self):

        print(
            "Initializing XAI explainer..."
        )

        self.device = DEVICE


        # ------------------------------------------
        # Load model
        # ------------------------------------------

        self.model = CheXpertDenseNet(
            num_classes=5
        ).to(
            self.device
        )


        checkpoint = torch.load(
            CHECKPOINT_PATH,
            map_location=self.device
        )


        self.model.load_state_dict(
            checkpoint["model_state_dict"]
        )

        self.model.eval()


        # ------------------------------------------
        # DenseNet target layer
        # ------------------------------------------

        self.target_layer = (
            self.model.model.features.norm5
        )


        print(
            "Grad-CAM target layer:"
        )

        print(
            "self.model.model.features.norm5"
        )


        print(
            "XAI explainer ready."
        )


    # --------------------------------------------------
    # Generate heatmap
    # --------------------------------------------------

    def generate_heatmap(
        self,
        image_path,
        finding
    ):

        image_path = Path(
            image_path
        )


        if not image_path.exists():

            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )


        if finding not in TARGETS:

            raise ValueError(
                f"Unknown finding: {finding}"
            )


        # ------------------------------------------
        # Load image
        # ------------------------------------------

        image = Image.open(
            image_path
        ).convert("RGB")


        # ------------------------------------------
        # Prepare model input
        # ------------------------------------------

        input_tensor = TRANSFORM(
            image
        ).unsqueeze(
            0
        ).to(
            self.device
        )


        # ------------------------------------------
        # Finding index
        # ------------------------------------------

        class_index = TARGETS.index(
            finding
        )


        # ------------------------------------------
        # Grad-CAM
        # ------------------------------------------

        cam = GradCAM(
            model=self.model,
            target_layers=[
                self.target_layer
            ]
        )


        targets = [
            ClassifierOutputTarget(
                class_index
            )
        ]


        grayscale_cam = cam(
            input_tensor=input_tensor,
            targets=targets
        )[0]


        # ------------------------------------------
        # Prepare original image
        # ------------------------------------------

        display_image = image.resize(
            (320, 320)
        )


        rgb_image = (
            np.asarray(
                display_image
            ).astype(
                np.float32
            )
            / 255.0
        )


        # ------------------------------------------
        # Overlay heatmap
        # ------------------------------------------

        visualization = show_cam_on_image(
            rgb_image,
            grayscale_cam,
            use_rgb=True
        )


        return visualization


# --------------------------------------------------
# Standalone test
# --------------------------------------------------

if __name__ == "__main__":

    test_image = (
        PROJECT_ROOT
        / "data"
        / "train"
        / "patient00007"
        / "study1"
        / "view1_frontal.jpg"
    )


    output_directory = (
        PROJECT_ROOT
        / "outputs"
        / "xai"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )


    explainer = XRayExplainer()


    print()
    print(
        "=" * 70
    )

    print(
        "GENERATING TEST GRAD-CAM"
    )

    print(
        "=" * 70
    )


    for finding in TARGETS:

        print()
        print(
            f"Generating: {finding}"
        )


        heatmap = (
            explainer.generate_heatmap(
                test_image,
                finding
            )
        )


        filename = (
            finding
            .lower()
            .replace(
                " ",
                "_"
            )
            + "_inference_gradcam.jpg"
        )


        output_path = (
            output_directory
            / filename
        )


        Image.fromarray(
            heatmap
        ).save(
            output_path
        )


        print(
            "Saved:"
        )

        print(
            output_path
        )


    print()
    print(
        "=" * 70
    )

    print(
        "XAI TEST COMPLETED"
    )

    print(
        "=" * 70
    )