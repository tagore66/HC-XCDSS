import sys
import json
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image


# --------------------------------------------------
# Project paths
# --------------------------------------------------

sys.path.append("src/data")
sys.path.append("src/models")

from densenet import CheXpertDenseNet


# --------------------------------------------------
# Configuration
# --------------------------------------------------

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

CHECKPOINT_PATH = (
    "models/checkpoints/"
    "best_densenet121_balanced.pth"
)

THRESHOLD_PATH = (
    "models/checkpoints/"
    "optimal_thresholds_balanced.json"
)


TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]


# --------------------------------------------------
# Image preprocessing
# --------------------------------------------------

transform = transforms.Compose([

    transforms.Resize(
        (224, 224)
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
# Load model
# --------------------------------------------------

print(
    "Device:",
    DEVICE
)

if torch.cuda.is_available():

    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )


print()
print(
    "Loading balanced model..."
)


model = CheXpertDenseNet(
    num_classes=5
).to(DEVICE)


checkpoint = torch.load(
    CHECKPOINT_PATH,
    map_location=DEVICE
)


model.load_state_dict(
    checkpoint["model_state_dict"]
)

model.eval()


print(
    "Checkpoint epoch:",
    checkpoint["epoch"]
)

print(
    "Checkpoint validation loss:",
    checkpoint["validation_loss"]
)


# --------------------------------------------------
# Load thresholds
# --------------------------------------------------

with open(
    THRESHOLD_PATH,
    "r"
) as file:

    thresholds = json.load(file)


print()
print(
    "Loaded thresholds:"
)

for target in TARGETS:

    print(
        f"{target}: "
        f"{thresholds[target]:.2f}"
    )


# --------------------------------------------------
# Grad-CAM target layer
# --------------------------------------------------

target_layers = [
    model.model.features.denseblock4
]


# --------------------------------------------------
# Generate Grad-CAM
# --------------------------------------------------

def generate_gradcam(
    image_path,
    target_index,
    output_path
):

    print()
    print(
        f"Generating Grad-CAM for "
        f"{TARGETS[target_index]}"
    )


    # ----------------------------------------------
    # Load image
    # ----------------------------------------------

    image = Image.open(
        image_path
    ).convert("RGB")


    # ----------------------------------------------
    # Image used by the neural network
    # ----------------------------------------------

    input_tensor = transform(
        image
    ).unsqueeze(0).to(DEVICE)


    # ----------------------------------------------
    # Create visualization image
    #
    # This is the resized RGB image before
    # normalization.
    # ----------------------------------------------

    display_image = image.resize(
        (224, 224)
    )


    rgb_image = np.asarray(
        display_image
    ).astype(
        np.float32
    ) / 255.0


    # ----------------------------------------------
    # Create Grad-CAM
    # ----------------------------------------------

    cam = GradCAM(
        model=model,
        target_layers=target_layers
    )


    targets = [
        ClassifierOutputTarget(
            target_index
        )
    ]


    grayscale_cam = cam(
        input_tensor=input_tensor,
        targets=targets
    )


    grayscale_cam = grayscale_cam[0]


    # ----------------------------------------------
    # Create heatmap overlay
    # ----------------------------------------------

    visualization = show_cam_on_image(
        rgb_image,
        grayscale_cam,
        use_rgb=True
    )


    # ----------------------------------------------
    # Save result
    # ----------------------------------------------

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    # OpenCV expects BGR
    visualization = cv2.cvtColor(
        visualization,
        cv2.COLOR_RGB2BGR
    )


    cv2.imwrite(
        str(output_path),
        visualization
    )


    print(
        "Saved:"
    )

    print(
        output_path
    )


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    print()
    print("=" * 70)
    print(
        "GRAD-CAM MODULE READY"
    )
    print("=" * 70)

    print()
    print(
        "This module provides:"
    )

    print(
        "1. Balanced DenseNet121 loading"
    )

    print(
        "2. Finding-specific Grad-CAM"
    )

    print(
        "3. Heatmap generation"
    )

    print(
        "4. Heatmap image saving"
    )

    print()
    print(
        "Model loaded successfully."
    )