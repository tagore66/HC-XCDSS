import sys
import json
from pathlib import Path

import pandas as pd
import torch
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

OUTPUT_FILE = (
    "outputs/xai/positive_xray.txt"
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
    "Thresholds:"
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
    "Validation CSV rows:",
    len(validation_df)
)


# --------------------------------------------------
# Dataset
# --------------------------------------------------

dataset = CheXpertDataset(
    VALIDATION_CSV,
    transform=transform
)


loader = DataLoader(
    dataset,
    batch_size=4,
    shuffle=False,
    num_workers=0,
    pin_memory=True
)


print(
    "Validation images:",
    len(dataset)
)


# --------------------------------------------------
# Model
# --------------------------------------------------

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
# Search
# --------------------------------------------------

print()
print(
    "Searching for an X-ray with "
    "a detected finding..."
)


found = False

image_offset = 0


with torch.no_grad():

    for batch_index, (
        images,
        labels,
        masks
    ) in enumerate(loader):

        images = images.to(
            DEVICE,
            non_blocking=True
        )


        outputs = model(
            images
        )


        probabilities = torch.sigmoid(
            outputs
        ).cpu()


        for batch_position in range(
            len(images)
        ):

            prediction = probabilities[
                batch_position
            ]


            detected = []


            for index, target in enumerate(
                TARGETS
            ):

                probability = (
                    prediction[index]
                    .item()
                )

                threshold = thresholds[
                    target
                ]


                if probability >= threshold:

                    detected.append(
                        (
                            target,
                            probability,
                            threshold
                        )
                    )


            if detected:

                dataset_index = (
                    image_offset +
                    batch_position
                )


                # ----------------------------------
                # Get the matching image path
                # ----------------------------------

                relative_path = (
                    validation_df.iloc[
                        dataset_index
                    ]["Path"]
                )


                # ----------------------------------
                # Resolve actual Windows path
                # ----------------------------------

                image_path = Path(
                    relative_path
                )


                if not image_path.exists():

                    # Try relative to project root
                    image_path = (
                        Path.cwd() /
                        relative_path
                    )


                print()
                print("=" * 70)

                print(
                    "POSITIVE X-RAY FOUND"
                )

                print("=" * 70)

                print()

                print(
                    "Dataset index:",
                    dataset_index
                )

                print()

                print(
                    "CSV image path:"
                )

                print(
                    relative_path
                )

                print()

                print(
                    "Resolved image path:"
                )

                print(
                    image_path
                )

                print()

                print(
                    "Detected findings:"
                )


                for (
                    target,
                    probability,
                    threshold
                ) in detected:

                    print(
                        f"{target}: "
                        f"{probability:.4f} "
                        f"(threshold "
                        f"{threshold:.2f})"
                    )


                # ----------------------------------
                # Save information
                # ----------------------------------

                output_path = Path(
                    OUTPUT_FILE
                )

                output_path.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )


                with open(
                    output_path,
                    "w"
                ) as file:

                    file.write(
                        str(image_path)
                    )

                    file.write(
                        "\n\n"
                    )

                    for (
                        target,
                        probability,
                        threshold
                    ) in detected:

                        file.write(
                            f"{target}: "
                            f"{probability:.4f} "
                            f"(threshold "
                            f"{threshold:.2f})\n"
                        )


                print()

                print(
                    "Saved image information:"
                )

                print(
                    output_path
                )


                found = True

                break


        if found:

            break


        image_offset += len(images)


        if (batch_index + 1) % 500 == 0:

            print(
                f"Searched "
                f"{image_offset}/"
                f"{len(dataset)} images"
            )


# --------------------------------------------------
# Final result
# --------------------------------------------------

print()

if not found:

    print(
        "No positive X-ray was found."
    )

else:

    print(
        "Search completed successfully."
    )