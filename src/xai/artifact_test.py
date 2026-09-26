import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms


sys.path.append("src/models")

from densenet import CheXpertDenseNet


# --------------------------------------------------
# Configuration
# --------------------------------------------------

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

IMAGE_PATH = (
    "C:/HC-XCDSS/data/train/"
    "patient00007/study1/view1_frontal.jpg"
)

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
# Device information
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


# --------------------------------------------------
# Load model
# --------------------------------------------------

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
    "Model loaded."
)


# --------------------------------------------------
# Load original image
# --------------------------------------------------

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


# IMPORTANT:
# Do NOT resize the original image here.
#
# The transform() function below performs the
# exact 224x224 preprocessing used by the model.


original_array = np.asarray(
    image
).copy()


# --------------------------------------------------
# Create artifact-masked image
# --------------------------------------------------

masked_array = original_array.copy()

height, width, _ = masked_array.shape


# Suspected upper-left artifact region.
#
# We mask approximately:
#
#   15% of image height
#   20% of image width
#
# This is intentionally the same region used
# in the previous experiment.

mask_height = int(
    height * 0.15
)

mask_width = int(
    width * 0.20
)


# --------------------------------------------------
# Calculate replacement intensity
# --------------------------------------------------

# Use a nearby region to estimate the local
# appearance instead of inserting pure black.

reference_height = max(
    20,
    int(height * 0.02)
)

reference_width = max(
    20,
    int(width * 0.02)
)


reference_region = original_array[
    mask_height:
        min(
            mask_height + reference_height,
            height
        ),

    mask_width:
        min(
            mask_width + reference_width,
            width
        )
]


if reference_region.size > 0:

    fill_value = (
        reference_region
        .mean(axis=(0, 1))
        .astype(np.uint8)
    )

else:

    fill_value = np.array(
        [128, 128, 128],
        dtype=np.uint8
    )


# --------------------------------------------------
# Apply mask
# --------------------------------------------------

masked_array[
    0:mask_height,
    0:mask_width
] = fill_value


masked_image = Image.fromarray(
    masked_array
)


# --------------------------------------------------
# Save masked image
# --------------------------------------------------

output_directory = Path(
    "outputs/xai"
)

output_directory.mkdir(
    parents=True,
    exist_ok=True
)


masked_image_path = (
    output_directory /
    "artifact_masked_xray.jpg"
)


masked_image.save(
    masked_image_path
)


print()
print(
    "Original image:"
)

print(
    IMAGE_PATH
)

print()
print(
    "Masked region:"
)

print(
    f"Top-left: "
    f"{mask_width} x {mask_height} pixels"
)

print()
print(
    "Saved masked image:"
)

print(
    masked_image_path
)


# --------------------------------------------------
# Prediction function
# --------------------------------------------------

def predict(image):

    # Both original and masked images come
    # through this exact same preprocessing.

    tensor = transform(
        image
    ).unsqueeze(
        0
    ).to(DEVICE)


    with torch.no_grad():

        outputs = model(
            tensor
        )

        probabilities = torch.sigmoid(
            outputs
        )[0]


    return probabilities.cpu().numpy()


# --------------------------------------------------
# Original prediction
# --------------------------------------------------

print()
print(
    "=" * 75
)

print(
    "ORIGINAL IMAGE PREDICTIONS"
)

print(
    "=" * 75
)


original_predictions = predict(
    image
)


print()

for index, target in enumerate(
    TARGETS
):

    print(
        f"{target:<20} "
        f"{original_predictions[index]:.6f}"
    )


# --------------------------------------------------
# Masked prediction
# --------------------------------------------------

print()
print(
    "=" * 75
)

print(
    "MASKED IMAGE PREDICTIONS"
)

print(
    "=" * 75
)


masked_predictions = predict(
    masked_image
)


print()

for index, target in enumerate(
    TARGETS
):

    print(
        f"{target:<20} "
        f"{masked_predictions[index]:.6f}"
    )


# --------------------------------------------------
# Compare predictions
# --------------------------------------------------

print()
print(
    "=" * 75
)

print(
    "ARTIFACT SENSITIVITY ANALYSIS"
)

print(
    "=" * 75
)


print()

print(
    f"{'Finding':<20}"
    f"{'Original':>12}"
    f"{'Masked':>12}"
    f"{'Change':>12}"
    f"{'Relative %':>14}"
)

print(
    "-" * 70
)


for index, target in enumerate(
    TARGETS
):

    original = (
        original_predictions[index]
    )

    masked = (
        masked_predictions[index]
    )

    change = (
        masked - original
    )

    relative_change = (
        abs(change)
        /
        max(abs(original), 1e-8)
        * 100
    )


    print(
        f"{target:<20}"
        f"{original:>12.4f}"
        f"{masked:>12.4f}"
        f"{change:>12.4f}"
        f"{relative_change:>13.2f}%"
    )


# --------------------------------------------------
# Check prediction flips
# --------------------------------------------------

print()
print(
    "=" * 75
)

print(
    "PREDICTION FLIP ANALYSIS"
)

print(
    "=" * 75
)


print()

for index, target in enumerate(
    TARGETS
):

    original = (
        original_predictions[index]
    )

    masked = (
        masked_predictions[index]
    )

    # We intentionally do not use the
    # optimized thresholds here.
    #
    # This section simply checks whether
    # the probability itself changed.
    #
    # Threshold-based flip analysis will
    # be performed separately across many
    # images.

    print(
        f"{target:<20}"
        f"Change: {masked - original:+.6f}"
    )


# --------------------------------------------------
# Overall interpretation
# --------------------------------------------------

print()
print(
    "=" * 75
)

print(
    "INTERPRETATION"
)

print(
    "=" * 75
)


absolute_changes = np.abs(
    masked_predictions -
    original_predictions
)


max_change = np.max(
    absolute_changes
)

mean_change = np.mean(
    absolute_changes
)


print()

print(
    f"Maximum absolute change: "
    f"{max_change:.6f}"
)

print(
    f"Mean absolute change: "
    f"{mean_change:.6f}"
)

print()


if max_change < 0.05:

    print(
        "No large prediction change detected."
    )

    print(
        "The model appears relatively "
        "insensitive to this masked region."
    )


elif max_change < 0.15:

    print(
        "Moderate prediction changes detected."
    )

    print(
        "The masked region may contribute "
        "to some predictions."
    )


else:

    print(
        "LARGE prediction change detected."
    )

    print(
        "This is a potential artifact/"
        "shortcut-learning warning."
    )


print()
print(
    "Artifact sensitivity test completed."
)