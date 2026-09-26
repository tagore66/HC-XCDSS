import sys
import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from torchvision import transforms
from sklearn.metrics import (
    f1_score,
    recall_score,
    confusion_matrix
)


sys.path.append("src/data")
sys.path.append("src/models")

from dataset import CheXpertDataset
from densenet import CheXpertDenseNet
from metrics import TARGETS


DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
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


model = CheXpertDenseNet(
    num_classes=5
).to(DEVICE)


print()
print(
    "Loading balanced checkpoint..."
)


checkpoint = torch.load(
    CHECKPOINT_PATH,
    map_location=DEVICE
)


model.load_state_dict(
    checkpoint["model_state_dict"]
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
    ) in enumerate(validation_loader):

        images = images.to(
            DEVICE,
            non_blocking=True
        )

        outputs = model(images)

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


        if (batch_index + 1) % 500 == 0:

            print(
                f"Processed "
                f"{batch_index + 1}/"
                f"{len(validation_loader)}"
            )


all_predictions = np.concatenate(
    all_predictions
)

all_targets = np.concatenate(
    all_targets
)

all_masks = np.concatenate(
    all_masks
)


print()
print(
    "Predictions shape:",
    all_predictions.shape
)


print()
print("=" * 70)
print(
    "BALANCED MODEL THRESHOLD OPTIMIZATION"
)
print("=" * 70)

print(
    "Optimization criterion: "
    "Youden's J"
)


optimal_thresholds = {}


thresholds = np.arange(
    0.05,
    0.96,
    0.01
)


for index, target in enumerate(TARGETS):

    print()
    print("-" * 70)

    print(
        f"Finding: {target}"
    )


    valid = all_masks[:, index]


    y_true = all_targets[
        valid,
        index
    ]


    y_true = np.where(
        y_true == -1,
        0,
        y_true
    )


    y_scores = all_predictions[
        valid,
        index
    ]


    if len(y_true) == 0:

        print(
            "No valid labels."
        )

        continue


    best_threshold = 0.5

    best_j = -1

    best_f1 = 0

    best_sensitivity = 0

    best_specificity = 0


    for threshold in thresholds:

        y_pred = (
            y_scores >= threshold
        ).astype(int)


        tn, fp, fn, tp = confusion_matrix(
            y_true,
            y_pred,
            labels=[0, 1]
        ).ravel()


        sensitivity = (
            tp / (tp + fn)
            if (tp + fn) > 0
            else 0
        )


        specificity = (
            tn / (tn + fp)
            if (tn + fp) > 0
            else 0
        )


        j_score = (
            sensitivity +
            specificity -
            1
        )


        f1 = f1_score(
            y_true,
            y_pred,
            zero_division=0
        )


        if j_score > best_j:

            best_j = j_score

            best_threshold = threshold

            best_f1 = f1

            best_sensitivity = sensitivity

            best_specificity = specificity


    optimal_thresholds[target] = (
        float(best_threshold)
    )


    print(
        f"Optimal threshold: "
        f"{best_threshold:.2f}"
    )

    print(
        f"Youden's J: "
        f"{best_j:.4f}"
    )

    print(
        f"F1: "
        f"{best_f1:.4f}"
    )

    print(
        f"Sensitivity: "
        f"{best_sensitivity:.4f}"
    )

    print(
        f"Specificity: "
        f"{best_specificity:.4f}"
    )


Path(
    THRESHOLD_PATH
).parent.mkdir(
    parents=True,
    exist_ok=True
)


with open(
    THRESHOLD_PATH,
    "w"
) as file:

    json.dump(
        optimal_thresholds,
        file,
        indent=4
    )


print()
print("=" * 70)
print(
    "OPTIMAL BALANCED MODEL THRESHOLDS"
)
print("=" * 70)


for target, threshold in optimal_thresholds.items():

    print(
        f"{target}: "
        f"{threshold:.2f}"
    )


print()
print(
    "Saved to:"
)

print(
    THRESHOLD_PATH
)

print()
print("=" * 70)
print(
    "BALANCED THRESHOLD OPTIMIZATION COMPLETED"
)
print("=" * 70)