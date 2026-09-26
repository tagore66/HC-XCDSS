import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from torchvision import transforms
from torch.amp import autocast, GradScaler

sys.path.append("src/data")
sys.path.append("src/evaluation")

from dataset import CheXpertDataset
from densenet import CheXpertDenseNet
from loss import masked_balanced_bce_loss
from metrics import calculate_metrics


DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

BATCH_SIZE = 8
EPOCHS = 8
LEARNING_RATE = 1e-4

TRAIN_CSV = "data/splits/train_clean.csv"
VALIDATION_CSV = "data/splits/validation_clean.csv"

CHECKPOINT_DIR = Path(
    "models/checkpoints"
)

CHECKPOINT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CHECKPOINT_PATH = (
    CHECKPOINT_DIR /
    "best_densenet121_balanced.pth"
)


print("Device:", DEVICE)

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


train_dataset = CheXpertDataset(
    TRAIN_CSV,
    transform=transform
)

validation_dataset = CheXpertDataset(
    VALIDATION_CSV,
    transform=transform
)


train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=0,
    pin_memory=True
)

validation_loader = DataLoader(
    validation_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,
    pin_memory=True
)


print(
    "Training images:",
    len(train_dataset)
)

print(
    "Validation images:",
    len(validation_dataset)
)

print(
    "Training batches:",
    len(train_loader)
)

print(
    "Validation batches:",
    len(validation_loader)
)


model = CheXpertDenseNet(
    num_classes=5
).to(DEVICE)


optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=1e-4
)


scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="min",
    factor=0.5,
    patience=1,
    min_lr=1e-6
)


if DEVICE.type == "cuda":

    scaler = GradScaler("cuda")

else:

    scaler = GradScaler(
        "cuda",
        enabled=False
    )


best_validation_loss = float("inf")


for epoch in range(EPOCHS):

    print()
    print("=" * 60)
    print(
        f"Epoch {epoch + 1}/{EPOCHS}"
    )
    print("=" * 60)


    model.train()

    training_loss = 0.0


    for batch_index, (
        images,
        labels,
        masks
    ) in enumerate(train_loader):

        images = images.to(
            DEVICE,
            non_blocking=True
        )

        labels = labels.to(
            DEVICE,
            non_blocking=True
        )

        masks = masks.to(
            DEVICE,
            non_blocking=True
        )


        optimizer.zero_grad()


        with autocast(
            "cuda",
            enabled=(DEVICE.type == "cuda")
        ):

            outputs = model(images)

            loss = masked_balanced_bce_loss(
                outputs,
                labels,
                masks
            )


        scaler.scale(
            loss
        ).backward()


        scaler.step(
            optimizer
        )

        scaler.update()


        training_loss += loss.item()


        if (batch_index + 1) % 500 == 0:

            average_loss = (
                training_loss /
                (batch_index + 1)
            )

            print(
                f"Training batch "
                f"{batch_index + 1}/"
                f"{len(train_loader)} "
                f"Loss: {average_loss:.4f}"
            )


    training_loss /= len(
        train_loader
    )


    model.eval()

    validation_loss = 0.0

    all_predictions = []
    all_targets = []
    all_masks = []


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

            labels = labels.to(
                DEVICE,
                non_blocking=True
            )

            masks = masks.to(
                DEVICE,
                non_blocking=True
            )


            with autocast(
                "cuda",
                enabled=(DEVICE.type == "cuda")
            ):

                outputs = model(images)

                loss = masked_balanced_bce_loss(
                    outputs,
                    labels,
                    masks
                )


            validation_loss += loss.item()


            probabilities = torch.sigmoid(
                outputs
            )


            all_predictions.append(
                probabilities.cpu().numpy()
            )

            all_targets.append(
                labels.cpu().numpy()
            )

            all_masks.append(
                masks.cpu().numpy()
            )


            if (batch_index + 1) % 500 == 0:

                print(
                    f"Validation batch "
                    f"{batch_index + 1}/"
                    f"{len(validation_loader)}"
                )


    validation_loss /= len(
        validation_loader
    )


    scheduler.step(
        validation_loss
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


    metrics = calculate_metrics(
        all_predictions,
        all_targets,
        all_masks
    )


    print()

    print(
        f"Training Loss: "
        f"{training_loss:.4f}"
    )

    print(
        f"Validation Loss: "
        f"{validation_loss:.4f}"
    )

    print(
        f"Learning Rate: "
        f"{optimizer.param_groups[0]['lr']:.8f}"
    )

    print()


    for target, values in metrics.items():

        print(
            f"{target}: "
            f"AUC={values['ROC_AUC']:.4f} "
            f"PR-AUC={values['PR_AUC']:.4f} "
            f"F1={values['F1']:.4f} "
            f"Sens={values['Sensitivity']:.4f} "
            f"Spec={values['Specificity']:.4f}"
        )


    if validation_loss < best_validation_loss:

        best_validation_loss = validation_loss


        torch.save(
            {
                "epoch": epoch + 1,

                "model_state_dict":
                    model.state_dict(),

                "optimizer_state_dict":
                    optimizer.state_dict(),

                "scheduler_state_dict":
                    scheduler.state_dict(),

                "validation_loss":
                    validation_loss
            },

            CHECKPOINT_PATH
        )


        print()

        print(
            "Best balanced model saved:"
        )

        print(
            CHECKPOINT_PATH
        )


print()
print("=" * 60)
print(
    "BALANCED TRAINING COMPLETED"
)
print("=" * 60)