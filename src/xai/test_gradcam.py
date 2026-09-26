import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image


sys.path.append("src/data")
sys.path.append("src/models")

from dataset import CheXpertDataset
from densenet import CheXpertDenseNet


# --------------------------------------------------
# Configuration
# --------------------------------------------------

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

IMAGE_PATH = "C:/HC-XCDSS/data/train/patient00007/study1/view1_frontal.jpg"
CHECKPOINT_PATH = (
    "models/checkpoints/"
    "best_densenet121_balanced.pth"
)


TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]


THRESHOLDS = {
    "Atelectasis": 0.55,
    "Cardiomegaly": 0.56,
    "Consolidation": 0.46,
    "Edema": 0.47,
    "Pleural Effusion": 0.57
}


# --------------------------------------------------
# Transform
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
    "Balanced model loaded."
)


# --------------------------------------------------
# Load X-ray
# --------------------------------------------------

if IMAGE_PATH == "PUT_YOUR_XRAY_PATH_HERE":

    print()
    print(
        "ERROR: Set IMAGE_PATH to an actual X-ray."
    )

    sys.exit(1)


image_path = Path(
    IMAGE_PATH
)


if not image_path.exists():

    print()
    print(
        "ERROR: Image not found:"
    )

    print(
        image_path
    )

    sys.exit(1)


image = Image.open(
    image_path
).convert("RGB")


# --------------------------------------------------
# Prepare image
# --------------------------------------------------

input_tensor = transform(
    image
).unsqueeze(0).to(DEVICE)


# --------------------------------------------------
# Prediction
# --------------------------------------------------

print()
print(
    "Running prediction..."
)


with torch.no_grad():

    outputs = model(
        input_tensor
    )

    probabilities = torch.sigmoid(
        outputs
    )[0]


# --------------------------------------------------
# Display predictions
# --------------------------------------------------

print()
print("=" * 70)
print(
    "X-RAY PREDICTIONS"
)
print("=" * 70)


detected_indices = []


for index, target in enumerate(TARGETS):

    probability = (
        probabilities[index]
        .item()
    )

    threshold = THRESHOLDS[target]

    detected = (
        probability >= threshold
    )


    status = (
        "DETECTED"
        if detected
        else "NOT DETECTED"
    )


    print(
        f"{target:<20} "
        f"Probability: "
        f"{probability:.4f}  "
        f"Threshold: "
        f"{threshold:.2f}  "
        f"{status}"
    )


    if detected:

        detected_indices.append(
            index
        )


# --------------------------------------------------
# Grad-CAM
# --------------------------------------------------

if len(detected_indices) == 0:

    print()
    print(
        "No findings crossed their thresholds."
    )

    print(
        "No Grad-CAM heatmaps generated."
    )

    sys.exit(0)


print()
print(
    "=" * 70
)

print(
    "GENERATING GRAD-CAM"
)

print(
    "=" * 70
)


# Final convolutional feature layer
target_layers = [
    model.model.features.norm5
]


# Original image resized for visualization

display_image = image.resize(
    (224, 224)
)


rgb_image = np.asarray(
    display_image
).astype(
    np.float32
) / 255.0


output_directory = Path(
    "outputs/xai"
)

output_directory.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# Generate heatmap for every detected finding
# --------------------------------------------------

for index in detected_indices:

    target_name = TARGETS[index]

    print()
    print(
        f"Generating heatmap: "
        f"{target_name}"
    )


    cam = GradCAM(
        model=model,
        target_layers=target_layers
    )


    targets = [
        ClassifierOutputTarget(
            index
        )
    ]


    grayscale_cam = cam(
        input_tensor=input_tensor,
        targets=targets
    )[0]


    visualization = show_cam_on_image(
        rgb_image,
        grayscale_cam,
        use_rgb=True
    )


    output_path = (
        output_directory /
        f"{target_name.lower().replace(' ', '_')}_gradcam.jpg"
    )


    Image.fromarray(
        visualization
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
print("=" * 70)
print(
    "GRAD-CAM COMPLETED"
)
print("=" * 70)