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
from metrics import calculate_metrics, TARGETS


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


OUTPUT_DIRECTORY = Path(
    "outputs/evaluation"
)


OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)


REPORT_PATH = (
    OUTPUT_DIRECTORY
    / "balanced_model_validation.json"
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


checkpoint_epoch = checkpoint[
    "epoch"
]


checkpoint_validation_loss = checkpoint[
    "validation_loss"
]


print(
    "Checkpoint epoch:",
    checkpoint_epoch
)


print(
    "Checkpoint validation loss:",
    checkpoint_validation_loss
)


model.eval()


all_predictions = []
all_targets = []
all_masks = []


print()
print(
    "Running evaluation..."
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
                f"{len(validation_loader)} "
                f"batches"
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
    "Evaluation data collected."
)


print(
    "Predictions shape:",
    all_predictions.shape
)


print(
    "Targets shape:",
    all_targets.shape
)


print(
    "Masks shape:",
    all_masks.shape
)


metrics = calculate_metrics(

    all_predictions,

    all_targets,

    all_masks
)


report = {

    "model": {

        "architecture":
            "DenseNet121",

        "checkpoint":
            "best_densenet121_balanced.pth",

        "checkpoint_epoch":
            int(checkpoint_epoch),

        "validation_loss":
            float(
                checkpoint_validation_loss
            )
    },

    "dataset": {

        "validation_csv":
            VALIDATION_CSV,

        "validation_images":
            len(validation_dataset)
    },

    "findings":
        metrics
}


with open(
    REPORT_PATH,
    "w"
) as file:

    json.dump(
        report,
        file,
        indent=4
    )


print()
print("=" * 70)
print(
    "HC-XCDSS PRODUCTION-THRESHOLD "
    "VALIDATION RESULTS"
)
print("=" * 70)


for target in TARGETS:

    if target not in metrics:

        print()
        print(
            f"{target}: No valid data"
        )

        continue


    values = metrics[target]


    print()
    print(target)


    print(
        f"  Threshold:    "
        f"{values['Threshold']:.2f}"
    )


    print(
        f"  ROC-AUC:      "
        f"{values['ROC_AUC']:.4f}"
    )


    print(
        f"  PR-AUC:       "
        f"{values['PR_AUC']:.4f}"
    )


    print(
        f"  Precision:    "
        f"{values['Precision']:.4f}"
    )


    print(
        f"  Sensitivity:  "
        f"{values['Sensitivity']:.4f}"
    )


    print(
        f"  Specificity:  "
        f"{values['Specificity']:.4f}"
    )


    print(
        f"  F1:           "
        f"{values['F1']:.4f}"
    )


    print(
        f"  TN: {values['TN']} "
        f"FP: {values['FP']} "
        f"FN: {values['FN']} "
        f"TP: {values['TP']}"
    )


print()
print(
    "Validation report saved:"
)


print(
    REPORT_PATH
)


print()
print("=" * 70)
print(
    "HC-XCDSS VALIDATION COMPLETED"
)
print("=" * 70)