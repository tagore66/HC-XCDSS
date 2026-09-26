import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torchvision import transforms


sys.path.append("src/models")

from densenet import CheXpertDenseNet


DEVICE = torch.device(
    "cuda" if torch.cuda.is_available()
    else "cpu"
)

VALIDATION_CSV = (
    "data/splits/validation_clean.csv"
)

CHECKPOINT_PATH = (
    "models/checkpoints/"
    "best_densenet121_balanced.pth"
)

OUTPUT_PATH = (
    "outputs/evaluation/"
    "image_level_predictions.csv"
)

DATA_ROOT = Path("data")

TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]


transform = transforms.Compose([
    transforms.Resize((224, 224)),
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


print("Device:", DEVICE)

if torch.cuda.is_available():
    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )


df = pd.read_csv(
    VALIDATION_CSV
)

df["Path"] = df["Path"].astype(str)


def get_study_id(path):

    parts = Path(path).parts

    patient = None
    study = None

    for part in parts:

        if part.startswith("patient"):
            patient = part

        if part.startswith("study"):
            study = part

    if patient is None or study is None:
        return "UNKNOWN"

    return f"{patient}/{study}"


df["Study_ID"] = df["Path"].apply(
    get_study_id
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


print()
print(
    "Checkpoint epoch:",
    checkpoint["epoch"]
)

print(
    "Validation images:",
    len(df)
)

print()
print(
    "Generating reusable prediction table..."
)


records = []


with torch.no_grad():

    for index, row in df.iterrows():

        image_path = (
            DATA_ROOT
            / Path(
                row["Path"]
            ).relative_to(
                "CheXpert-v1.0-small"
            )
        )

        try:

            image = Image.open(
                image_path
            ).convert("RGB")

            tensor = transform(
                image
            ).unsqueeze(0).to(
                DEVICE
            )

            output = model(
                tensor
            )

            probabilities = torch.sigmoid(
                output
            )[0].cpu().numpy()


            record = {

                "Path":
                    row["Path"],

                "Patient_ID":
                    row["Patient_ID"],

                "Study_ID":
                    row["Study_ID"],

                "View":
                    row["Frontal/Lateral"],

                "AP_PA":
                    row["AP/PA"]
            }


            for i, target in enumerate(
                TARGETS
            ):

                record[
                    f"{target}_true"
                ] = row[target]

                record[
                    f"{target}_probability"
                ] = float(
                    probabilities[i]
                )


            records.append(
                record
            )


        except Exception as error:

            print(
                "ERROR:",
                row["Path"]
            )

            print(
                error
            )


        if (index + 1) % 1000 == 0:

            print(
                f"Processed "
                f"{index + 1}/"
                f"{len(df)}"
            )


result = pd.DataFrame(
    records
)


Path(
    OUTPUT_PATH
).parent.mkdir(
    parents=True,
    exist_ok=True
)


result.to_csv(
    OUTPUT_PATH,
    index=False
)


print()
print("=" * 80)
print(
    "IMAGE-LEVEL PREDICTION TABLE CREATED"
)
print("=" * 80)

print(
    "Rows:",
    len(result)
)

print(
    "Columns:",
    len(result.columns)
)

print()
print(
    "Saved:"
)

print(
    OUTPUT_PATH
)

print()
print(
    result.head().to_string(
        index=False
    )
)

print()
print(
    "Prediction table generation completed."
)