import sys
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms


# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.append(
    str(PROJECT_ROOT / "src" / "models")
)

from densenet import CheXpertDenseNet


# --------------------------------------------------
# Configuration
# --------------------------------------------------

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available()
    else "cpu"
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


# --------------------------------------------------
# FINAL VIEW-SPECIFIC THRESHOLDS
#
# These are the thresholds obtained from validation (Experiment 2).
# --------------------------------------------------

VIEW_THRESHOLDS = {

    "Frontal": {

        "Atelectasis": 0.4189,

        "Cardiomegaly": 0.5407,

        "Consolidation": 0.3573,

        "Edema": 0.5251,

        "Pleural Effusion": 0.4538
    },

    "Lateral": {

        "Atelectasis": 0.4189,

        "Cardiomegaly": 0.5407,

        "Consolidation": 0.3573,

        "Edema": 0.5251,

        "Pleural Effusion": 0.4538
    }
}


# --------------------------------------------------
# Image preprocessing
# --------------------------------------------------

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
# Predictor
# --------------------------------------------------

class XRayPredictor:

    def __init__(self):

        print(
            "Initializing X-ray predictor..."
        )

        self.device = DEVICE


        # ------------------------------------------
        # Validate checkpoint
        # ------------------------------------------

        if not CHECKPOINT_PATH.exists():

            raise FileNotFoundError(
                "Balanced model checkpoint not found: "
                f"{CHECKPOINT_PATH}"
            )


        # ------------------------------------------
        # Load DenseNet121
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


        print(
            "Balanced DenseNet121 loaded."
        )

        print(
            "Checkpoint epoch:",
            checkpoint["epoch"]
        )

        print(
            "Validation loss:",
            checkpoint["validation_loss"]
        )

        print(
            "Device:",
            self.device
        )


    # --------------------------------------------------
    # Validate view
    # --------------------------------------------------

    def validate_view(
        self,
        view
    ):

        if view not in VIEW_THRESHOLDS:

            raise ValueError(
                "Invalid X-ray view. "
                "Expected 'Frontal' or 'Lateral'."
            )


        return view


    # --------------------------------------------------
    # Validate image
    # --------------------------------------------------

    def validate_image(
        self,
        image_path
    ):

        image_path = Path(
            image_path
        )


        if not image_path.exists():

            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )


        try:

            image = Image.open(
                image_path
            ).convert("RGB")

        except Exception as error:

            raise ValueError(
                f"Unable to read image: {error}"
            )


        return image


    # --------------------------------------------------
    # Predict
    # --------------------------------------------------

    def predict(
        self,
        image_path,
        view="Frontal"
    ):

        # ------------------------------------------
        # Validate inputs
        # ------------------------------------------

        view = self.validate_view(
            view
        )


        image = self.validate_image(
            image_path
        )


        # ------------------------------------------
        # Preprocess
        # ------------------------------------------

        tensor = TRANSFORM(
            image
        ).unsqueeze(
            0
        ).to(
            self.device
        )


        # ------------------------------------------
        # Model inference
        # ------------------------------------------

        with torch.no_grad():

            outputs = self.model(
                tensor
            )

            probabilities = torch.sigmoid(
                outputs
            )[0]


        probabilities = (
            probabilities
            .cpu()
            .numpy()
        )


        # ------------------------------------------
        # Select thresholds for view
        # ------------------------------------------

        thresholds = VIEW_THRESHOLDS[
            view
        ]


        # ------------------------------------------
        # Build findings
        # ------------------------------------------

        findings = {}


        for index, target in enumerate(
            TARGETS
        ):

            probability = float(
                probabilities[index]
            )


            threshold = float(
                thresholds[target]
            )


            detected = (
                probability >= threshold
            )


            findings[target] = {

                "probability":
                    probability,

                "threshold":
                    threshold,

                "detected":
                    bool(detected)
            }


        # ------------------------------------------
        # Final result
        # ------------------------------------------

        return {

            "image":
                str(image_path),

            "view":
                view,

            "findings":
                findings
        }


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


    predictor = XRayPredictor()


    # ----------------------------------------------
    # Test frontal inference
    # ----------------------------------------------

    result = predictor.predict(
        test_image,
        view="Frontal"
    )


    print()
    print("=" * 70)
    print("X-RAY INFERENCE RESULT")
    print("=" * 70)


    print()
    print(
        "View:",
        result["view"]
    )


    for target, finding in (
        result["findings"].items()
    ):

        print()

        print(
            target
        )

        print(
            f"  Probability: "
            f"{finding['probability']:.4f}"
        )

        print(
            f"  Threshold:   "
            f"{finding['threshold']:.2f}"
        )

        print(
            f"  Detected:    "
            f"{finding['detected']}"
        )


    print()
    print("=" * 70)
    print("INFERENCE TEST COMPLETED")
    print("=" * 70)