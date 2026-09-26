import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch.utils.data import DataLoader
from torchvision import transforms


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

VALIDATION_CSV = (
    "data/splits/validation_clean.csv"
)

CHECKPOINT_PATH = (
    "models/checkpoints/"
    "best_densenet121_balanced.pth"
)

THRESHOLD_PATH = (
    "models/checkpoints/"
    "optimal_thresholds_balanced.json"
)

NUM_IMAGES = 100

BATCH_SIZE = 4

TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]


# --------------------------------------------------
# Image path configuration
# --------------------------------------------------

# Your CSV contains paths like:
#
# CheXpert-v1.0-small/train/patient00007/...
#
# Your actual images are located under:
#
# C:/HC-XCDSS/data/train/...
#
# Therefore we replace the CSV prefix.

CSV_PREFIX = (
    "CheXpert-v1.0-small/train/"
)

REAL_PREFIX = (
    "C:/HC-XCDSS/data/train/"
)


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
# Device
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
# Load validation CSV
# --------------------------------------------------

validation_df = pd.read_csv(
    VALIDATION_CSV
)


print()
print(
    "Validation images:",
    len(validation_df)
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
    "Balanced model loaded."
)


# --------------------------------------------------
# Select images
# --------------------------------------------------

num_images = min(
    NUM_IMAGES,
    len(validation_df)
)


selected_df = validation_df.iloc[
    :num_images
].copy()


print()
print(
    f"Testing {num_images} validation images."
)


# --------------------------------------------------
# Convert CSV path to real path
# --------------------------------------------------

def resolve_image_path(
    csv_path
):

    csv_path = str(
        csv_path
    )


    if csv_path.startswith(
        CSV_PREFIX
    ):

        relative_path = (
            csv_path[
                len(CSV_PREFIX):
            ]
        )

        return Path(
            REAL_PREFIX
            +
            relative_path
        )


    # Fallback

    return Path(
        csv_path
    )


# --------------------------------------------------
# Create masked image
# --------------------------------------------------

def create_masked_image(
    image
):

    array = np.asarray(
        image
    ).copy()


    height, width, _ = (
        array.shape
    )


    # Same masking strategy used
    # in the single-image test.

    mask_height = int(
        height * 0.15
    )

    mask_width = int(
        width * 0.20
    )


    reference_height = max(
        20,
        int(height * 0.02)
    )

    reference_width = max(
        20,
        int(width * 0.02)
    )


    reference_region = array[
        mask_height:
            min(
                mask_height +
                reference_height,
                height
            ),

        mask_width:
            min(
                mask_width +
                reference_width,
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


    array[
        0:mask_height,
        0:mask_width
    ] = fill_value


    return Image.fromarray(
        array
    )


# --------------------------------------------------
# Prediction function
# --------------------------------------------------

def predict_batch(
    images
):

    tensors = torch.stack(
        [
            transform(image)
            for image in images
        ]
    ).to(
        DEVICE
    )


    with torch.no_grad():

        outputs = model(
            tensors
        )

        probabilities = torch.sigmoid(
            outputs
        )


    return probabilities.cpu().numpy()


# --------------------------------------------------
# Storage
# --------------------------------------------------

original_predictions = []

masked_predictions = []

processed_paths = []

skipped_images = 0


# --------------------------------------------------
# Process images
# --------------------------------------------------

print()
print(
    "=" * 75
)

print(
    "RUNNING ARTIFACT ROBUSTNESS TEST"
)

print(
    "=" * 75
)


for start in range(
    0,
    num_images,
    BATCH_SIZE
):

    end = min(
        start + BATCH_SIZE,
        num_images
    )


    batch_df = selected_df.iloc[
        start:end
    ]


    original_images = []

    masked_images = []

    batch_paths = []


    for _, row in batch_df.iterrows():

        image_path = resolve_image_path(
            row["Path"]
        )


        if not image_path.exists():

            print()
            print(
                "WARNING: Image not found:"
            )

            print(
                image_path
            )

            skipped_images += 1

            continue


        try:

            image = Image.open(
                image_path
            ).convert("RGB")

        except Exception as error:

            print()
            print(
                "WARNING: Could not load:"
            )

            print(
                image_path
            )

            print(
                "Error:",
                error
            )

            skipped_images += 1

            continue


        masked_image = (
            create_masked_image(
                image
            )
        )


        original_images.append(
            image
        )

        masked_images.append(
            masked_image
        )

        batch_paths.append(
            str(image_path)
        )


    if not original_images:

        continue


    original_batch_predictions = (
        predict_batch(
            original_images
        )
    )


    masked_batch_predictions = (
        predict_batch(
            masked_images
        )
    )


    original_predictions.extend(
        original_batch_predictions
    )

    masked_predictions.extend(
        masked_batch_predictions
    )

    processed_paths.extend(
        batch_paths
    )


    processed = len(
        original_predictions
    )


    print(
        f"Processed "
        f"{processed}/"
        f"{num_images}"
    )


# --------------------------------------------------
# Convert to numpy
# --------------------------------------------------

original_predictions = np.asarray(
    original_predictions
)

masked_predictions = np.asarray(
    masked_predictions
)


print()
print(
    "=" * 75
)

print(
    "DATA COLLECTION COMPLETED"
)

print(
    "=" * 75
)


print()

print(
    "Processed images:",
    len(original_predictions)
)

print(
    "Skipped images:",
    skipped_images
)


if len(original_predictions) == 0:

    print()
    print(
        "ERROR: No images were processed."
    )

    sys.exit(1)


# --------------------------------------------------
# Calculate changes
# --------------------------------------------------

absolute_changes = np.abs(
    masked_predictions -
    original_predictions
)


signed_changes = (
    masked_predictions -
    original_predictions
)


# --------------------------------------------------
# Robustness analysis
# --------------------------------------------------

print()
print(
    "=" * 75
)

print(
    "ARTIFACT ROBUSTNESS RESULTS"
)

print(
    "=" * 75
)


print()

print(
    f"{'Finding':<20}"
    f"{'Mean |Change|':>16}"
    f"{'Median |Change|':>18}"
    f"{'Max |Change|':>15}"
)


print(
    "-" * 75
)


for index, target in enumerate(
    TARGETS
):

    changes = (
        absolute_changes[:, index]
    )


    print(
        f"{target:<20}"
        f"{changes.mean():>16.6f}"
        f"{np.median(changes):>18.6f}"
        f"{changes.max():>15.6f}"
    )


# --------------------------------------------------
# Threshold-based prediction flips
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

print(
    f"{'Finding':<20}"
    f"{'Threshold':>12}"
    f"{'Original+':>14}"
    f"{'Masked+':>12}"
    f"{'Flips':>10}"
    f"{'Flip %':>10}"
)


print(
    "-" * 80
)


flip_counts = {}


for index, target in enumerate(
    TARGETS
):

    threshold = float(
        thresholds[target]
    )


    original_positive = (
        original_predictions[:, index]
        >= threshold
    )


    masked_positive = (
        masked_predictions[:, index]
        >= threshold
    )


    flips = (
        original_positive
        !=
        masked_positive
    )


    flip_count = int(
        flips.sum()
    )


    flip_percentage = (
        flip_count /
        len(original_predictions)
        *
        100
    )


    flip_counts[target] = (
        flip_count
    )


    print(
        f"{target:<20}"
        f"{threshold:>12.2f}"
        f"{original_positive.sum():>14}"
        f"{masked_positive.sum():>12}"
        f"{flip_count:>10}"
        f"{flip_percentage:>9.2f}%"
    )


# --------------------------------------------------
# Overall statistics
# --------------------------------------------------

print()
print(
    "=" * 75
)

print(
    "OVERALL ROBUSTNESS"
)

print(
    "=" * 75
)


mean_absolute_change = (
    absolute_changes.mean()
)

maximum_absolute_change = (
    absolute_changes.max()
)


total_flips = sum(
    flip_counts.values()
)

possible_predictions = (
    len(original_predictions)
    *
    len(TARGETS)
)


overall_flip_rate = (
    total_flips /
    possible_predictions
    *
    100
)


print()

print(
    f"Mean absolute probability change: "
    f"{mean_absolute_change:.6f}"
)

print(
    f"Maximum probability change: "
    f"{maximum_absolute_change:.6f}"
)

print(
    f"Total prediction flips: "
    f"{total_flips}"
)

print(
    f"Overall flip rate: "
    f"{overall_flip_rate:.2f}%"
)


# --------------------------------------------------
# Interpretation
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


print()


if overall_flip_rate < 2:

    print(
        "LOW ARTIFACT SENSITIVITY"
    )

    print(
        "The model shows relatively stable "
        "predictions when the suspected "
        "artifact region is masked."
    )


elif overall_flip_rate < 10:

    print(
        "MODERATE ARTIFACT SENSITIVITY"
    )

    print(
        "Some predictions are affected by "
        "the masked region."
    )

    print(
        "Further investigation is recommended."
    )


else:

    print(
        "HIGH ARTIFACT SENSITIVITY"
    )

    print(
        "The model may be relying on "
        "image artifacts or shortcuts."
    )

    print(
        "Do NOT treat the current XAI "
        "pipeline as production-ready."
    )


# --------------------------------------------------
# Save numerical results
# --------------------------------------------------

output_directory = Path(
    "outputs/xai"
)

output_directory.mkdir(
    parents=True,
    exist_ok=True
)


results = {

    "images_tested":
        int(len(original_predictions)),

    "images_skipped":
        int(skipped_images),

    "mean_absolute_probability_change":
        float(mean_absolute_change),

    "maximum_absolute_probability_change":
        float(maximum_absolute_change),

    "total_prediction_flips":
        int(total_flips),

    "overall_flip_rate_percent":
        float(overall_flip_rate),

    "per_finding_flip_counts":
        flip_counts
}


results_path = (
    output_directory /
    "artifact_robustness_results.json"
)


with open(
    results_path,
    "w"
) as file:

    json.dump(
        results,
        file,
        indent=4
    )


print()
print(
    "Results saved:"
)

print(
    results_path
)


print()
print(
    "=" * 75
)

print(
    "ARTIFACT ROBUSTNESS TEST COMPLETED"
)

print(
    "=" * 75
)