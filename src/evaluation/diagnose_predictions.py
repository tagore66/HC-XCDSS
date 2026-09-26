import sys
import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from torchvision import transforms


sys.path.append("src/data")
sys.path.append("src/models")

from dataset import CheXpertDataset
from densenet import CheXpertDenseNet
from metrics import TARGETS


DEVICE = torch.device(
    "cuda" if torch.cuda.is_available()
    else "cpu"
)

BATCH_SIZE = 4

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

OUTPUT_DIRECTORY = Path(
    "outputs/evaluation"
)

OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_PATH = (
    OUTPUT_DIRECTORY
    / "prediction_diagnostics.json"
)


print(
    "Device:",
    DEVICE
)

if torch.cuda.is_available():

    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )


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


validation_dataset = CheXpertDataset(
    VALIDATION_CSV,
    transform=transform
)


validation_loader = DataLoader(

    validation_dataset,

    batch_size=BATCH_SIZE,

    shuffle=False,

    num_workers=0,

    pin_memory=True
)


print(
    "Validation images:",
    len(validation_dataset)
)


print(
    "Validation batches:",
    len(validation_loader)
)


with open(
    THRESHOLD_PATH,
    "r"
) as file:

    thresholds = json.load(file)


print()
print(
    "Loaded balanced-model thresholds:"
)

for target in TARGETS:

    print(
        f"{target}: "
        f"{thresholds[target]:.2f}"
    )


model = CheXpertDenseNet(
    num_classes=5
).to(
    DEVICE
)


print()
print(
    "Loading balanced checkpoint..."
)


checkpoint = torch.load(
    CHECKPOINT_PATH,
    map_location=DEVICE
)


model.load_state_dict(
    checkpoint[
        "model_state_dict"
    ]
)


print(
    "Checkpoint epoch:",
    checkpoint["epoch"]
)

print(
    "Checkpoint validation loss:",
    checkpoint["validation_loss"]
)


model.eval()


all_predictions = []
all_targets = []
all_masks = []


print()
print(
    "Running validation..."
)


with torch.no_grad():

    for batch_index, (
        images,
        labels,
        masks
    ) in enumerate(
        validation_loader
    ):

        images = images.to(
            DEVICE,
            non_blocking=True
        )


        outputs = model(
            images
        )


        probabilities = torch.sigmoid(
            outputs
        )


        all_predictions.append(
            probabilities.cpu().numpy()
        )


        all_targets.append(
            labels.numpy()
        )


        all_masks.append(
            masks.numpy()
        )


        if (
            batch_index + 1
        ) % 500 == 0:

            print(
                f"Processed "
                f"{batch_index + 1}/"
                f"{len(validation_loader)}"
            )


predictions = np.concatenate(
    all_predictions
)

targets = np.concatenate(
    all_targets
)

masks = np.concatenate(
    all_masks
)


print()
print(
    "Validation predictions collected."
)


diagnostics = {}


for index, target in enumerate(
    TARGETS
):

    threshold = float(
        thresholds[target]
    )


    valid = masks[:, index]


    y_true = targets[
        valid,
        index
    ]


    y_scores = predictions[
        valid,
        index
    ]


    y_true = np.where(
        y_true == -1,
        0,
        y_true
    )


    valid_indices = np.where(
        valid
    )[0]


    false_positives = []
    false_negatives = []
    true_positives = []
    true_negatives = []


    for local_index, original_index in enumerate(
        valid_indices
    ):

        probability = float(
            y_scores[local_index]
        )

        ground_truth = int(
            y_true[local_index]
        )

        predicted = int(
            probability >= threshold
        )


        row = validation_dataset.data.iloc[
            original_index
        ]


        image_path = str(
            row["Path"]
        )


        record = {

            "image": image_path,

            "probability":
                probability,

            "threshold":
                threshold,

            "ground_truth":
                ground_truth,

            "prediction":
                predicted
        }


        if (
            ground_truth == 0
            and predicted == 1
        ):

            record["error_type"] = (
                "FALSE_POSITIVE"
            )

            false_positives.append(
                record
            )


        elif (
            ground_truth == 1
            and predicted == 0
        ):

            record["error_type"] = (
                "FALSE_NEGATIVE"
            )

            false_negatives.append(
                record
            )


        elif (
            ground_truth == 1
            and predicted == 1
        ):

            record["error_type"] = (
                "TRUE_POSITIVE"
            )

            true_positives.append(
                record
            )


        elif (
            ground_truth == 0
            and predicted == 0
        ):

            record["error_type"] = (
                "TRUE_NEGATIVE"
            )

            true_negatives.append(
                record
            )


    false_positives.sort(
        key=lambda x:
        x["probability"],
        reverse=True
    )


    false_negatives.sort(
        key=lambda x:
        x["probability"]
    )


    true_positives.sort(
        key=lambda x:
        x["probability"],
        reverse=True
    )


    true_negatives.sort(
        key=lambda x:
        x["probability"]
    )


    diagnostics[target] = {

        "threshold":
            threshold,

        "false_positive_count":
            len(false_positives),

        "false_negative_count":
            len(false_negatives),

        "true_positive_count":
            len(true_positives),

        "true_negative_count":
            len(true_negatives),

        "false_positives":
            false_positives,

        "false_negatives":
            false_negatives,

        "true_positives":
            true_positives,

        "true_negatives":
            true_negatives
    }


    print()
    print("=" * 75)
    print(target)
    print("=" * 75)


    print(
        "Threshold:",
        threshold
    )


    print(
        "False Positives:",
        len(false_positives)
    )


    print(
        "False Negatives:",
        len(false_negatives)
    )


    print(
        "True Positives:",
        len(true_positives)
    )


    print(
        "True Negatives:",
        len(true_negatives)
    )


    print()
    print(
        "Top high-confidence false positives:"
    )


    for record in false_positives[:5]:

        print(
            f"  {record['probability']:.4f} "
            f"{record['image']}"
        )


    print()
    print(
        "Top high-confidence false negatives:"
    )


    for record in false_negatives[:5]:

        print(
            f"  {record['probability']:.4f} "
            f"{record['image']}"
        )


result = {

    "model": {

        "architecture":
            "DenseNet121",

        "checkpoint":
            "best_densenet121_balanced.pth",

        "epoch":
            int(checkpoint["epoch"]),

        "validation_loss":
            float(
                checkpoint[
                    "validation_loss"
                ]
            )
    },

    "dataset": {

        "validation_csv":
            VALIDATION_CSV,

        "validation_images":
            len(validation_dataset)
    },

    "findings":
        diagnostics
}


with open(
    OUTPUT_PATH,
    "w"
) as file:

    json.dump(
        result,
        file,
        indent=4
    )


print()
print("=" * 75)
print(
    "PREDICTION DIAGNOSTICS COMPLETED"
)
print("=" * 75)


print()
print(
    "Diagnostic report saved:"
)

print(
    OUTPUT_PATH
)