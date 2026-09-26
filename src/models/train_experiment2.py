"""
HC-XCDSS Experiment 2: Resolution Isolation (320x320, NO Augmentation)

Configuration:
- Input Resolution: 320x320
- Training Augmentation: NONE (Deterministic Resize(320, 320) + Normalize)
- Validation Preprocessing: Deterministic Resize(320, 320) + Normalize
- Backbone: DenseNet-121 (Pretrained ImageNet weights)
- Target Findings: 5 CheXpert conditions
- Loss: masked_balanced_bce_loss
- Optimizer: AdamW (lr=1e-4, weight_decay=1e-4)
- Scheduler: ReduceLROnPlateau (mode=min, factor=0.5, patience=1, min_lr=1e-6)
- Checkpoint: models/checkpoints/densenet121_320_noaug_best.pth
"""

import sys
import time
import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from torchvision import transforms
from torch.amp import autocast, GradScaler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "src" / "data"))
sys.path.append(str(PROJECT_ROOT / "src" / "models"))
sys.path.append(str(PROJECT_ROOT / "src" / "evaluation"))

from dataset import CheXpertDataset
from densenet import CheXpertDenseNet
from loss import masked_balanced_bce_loss
from metrics import calculate_metrics

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BATCH_SIZE = 8
EPOCHS = 8
LEARNING_RATE = 1e-4

TRAIN_CSV = str(PROJECT_ROOT / "data" / "splits" / "train_clean.csv")
VALIDATION_CSV = str(PROJECT_ROOT / "data" / "splits" / "validation_clean.csv")

CHECKPOINT_DIR = PROJECT_ROOT / "models" / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_PATH = CHECKPOINT_DIR / "densenet121_320_noaug_best.pth"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "evaluation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_PATH = OUTPUT_DIR / "experiment2_history.json"
METRICS_PATH = OUTPUT_DIR / "experiment2_metrics.json"

TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]


def main():
    print("=" * 85)
    print("HC-XCDSS EXPERIMENT 2: 320x320 RESOLUTION ISOLATION (NO AUGMENTATION)")
    print("=" * 85)
    print(f"Device: {DEVICE}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    print(f"Target Checkpoint: {CHECKPOINT_PATH}")
    print(f"Resolution: 320x320 | Augmentation: NONE | Batch Size: {BATCH_SIZE} | Total Epochs: {EPOCHS}")

    # Deterministic Preprocessing (No Augmentation)
    train_transform = transforms.Compose([
        transforms.Resize((320, 320)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

    val_transform = transforms.Compose([
        transforms.Resize((320, 320)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

    train_dataset = CheXpertDataset(TRAIN_CSV, transform=train_transform)
    validation_dataset = CheXpertDataset(VALIDATION_CSV, transform=val_transform)

    num_workers = 2 if DEVICE.type == "cuda" else 0

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=(DEVICE.type == "cuda")
    )

    validation_loader = DataLoader(
        validation_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=(DEVICE.type == "cuda")
    )

    print(f"Training images: {len(train_dataset)} ({len(train_loader)} batches)")
    print(f"Validation images: {len(validation_dataset)} ({len(validation_loader)} batches)")

    model = CheXpertDenseNet(num_classes=5).to(DEVICE)

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

    scaler = GradScaler("cuda", enabled=(DEVICE.type == "cuda"))

    best_validation_loss = float("inf")
    best_epoch = 0
    history = []
    best_metrics = {}

    for epoch in range(EPOCHS):
        epoch_start_time = time.time()
        current_lr = optimizer.param_groups[0]["lr"]

        print()
        print("=" * 60)
        print(f"Epoch {epoch + 1}/{EPOCHS} (Current LR: {current_lr:.8f})")
        print("=" * 60)

        model.train()
        running_train_loss = 0.0

        for batch_idx, (images, labels, masks) in enumerate(train_loader):
            images = images.to(DEVICE, non_blocking=True)
            labels = labels.to(DEVICE, non_blocking=True)
            masks = masks.to(DEVICE, non_blocking=True)

            optimizer.zero_grad()

            with autocast("cuda", enabled=(DEVICE.type == "cuda")):
                outputs = model(images)
                loss = masked_balanced_bce_loss(outputs, labels, masks)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_train_loss += loss.item()

            if (batch_idx + 1) % 1000 == 0 or (batch_idx + 1) == len(train_loader):
                avg_b_loss = running_train_loss / (batch_idx + 1)
                print(f"Train batch {batch_idx + 1}/{len(train_loader)} | Running Loss: {avg_b_loss:.4f}")

        train_loss = running_train_loss / len(train_loader)

        # Validation Pass
        model.eval()
        running_val_loss = 0.0
        all_preds = []
        all_targs = []
        all_msks = []

        with torch.no_grad():
            for batch_idx, (images, labels, masks) in enumerate(validation_loader):
                images = images.to(DEVICE, non_blocking=True)
                labels = labels.to(DEVICE, non_blocking=True)
                masks = masks.to(DEVICE, non_blocking=True)

                with autocast("cuda", enabled=(DEVICE.type == "cuda")):
                    outputs = model(images)
                    loss = masked_balanced_bce_loss(outputs, labels, masks)

                running_val_loss += loss.item()

                probs = torch.sigmoid(outputs)
                all_preds.append(probs.cpu().numpy())
                all_targs.append(labels.cpu().numpy())
                all_msks.append(masks.cpu().numpy())

        val_loss = running_val_loss / len(validation_loader)
        scheduler.step(val_loss)

        epoch_duration = time.time() - epoch_start_time

        all_preds = np.concatenate(all_preds)
        all_targs = np.concatenate(all_targs)
        all_msks = np.concatenate(all_msks)

        epoch_metrics = calculate_metrics(all_preds, all_targs, all_msks)

        print()
        print(f"Epoch {epoch + 1} Summary:")
        print(f"  Train Loss:       {train_loss:.4f}")
        print(f"  Validation Loss:  {val_loss:.4f}")
        print(f"  Learning Rate:    {current_lr:.8f}")
        print(f"  Duration:         {epoch_duration:.1f}s ({epoch_duration/60:.2f} mins)")
        print()

        for target in TARGETS:
            m = epoch_metrics.get(target, {})
            auc = m.get("ROC_AUC", 0.0)
            pr_auc = m.get("PR_AUC", 0.0)
            f1 = m.get("F1", 0.0)
            sens = m.get("Sensitivity", 0.0)
            spec = m.get("Specificity", 0.0)
            print(f"  {target:<18} AUC: {auc:.4f} | PR-AUC: {pr_auc:.4f} | F1: {f1:.4f} | Sens: {sens:.4f} | Spec: {spec:.4f}")

        epoch_record = {
            "epoch": epoch + 1,
            "train_loss": round(train_loss, 6),
            "validation_loss": round(val_loss, 6),
            "learning_rate": current_lr,
            "duration_seconds": round(epoch_duration, 2),
            "metrics": {
                k: {mk: round(float(mv), 6) for mk, mv in v.items()}
                for k, v in epoch_metrics.items()
            }
        }
        history.append(epoch_record)

        with open(HISTORY_PATH, "w") as hf:
            json.dump(history, hf, indent=2)

        if val_loss < best_validation_loss:
            best_validation_loss = val_loss
            best_epoch = epoch + 1
            best_metrics = epoch_metrics

            torch.save(
                {
                    "epoch": epoch + 1,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "scheduler_state_dict": scheduler.state_dict(),
                    "validation_loss": val_loss,
                    "train_loss": train_loss,
                    "resolution": (320, 320),
                    "augmentation": "NONE",
                    "targets": TARGETS,
                },
                CHECKPOINT_PATH
            )

            print(f"\n>>> Best model checkpoint updated at Epoch {epoch + 1} (Val Loss: {val_loss:.6f}) -> {CHECKPOINT_PATH}")

    summary_data = {
        "experiment": "Experiment 2: 320x320 Resolution Isolation (NO Augmentation)",
        "checkpoint_path": str(CHECKPOINT_PATH),
        "total_epochs_completed": EPOCHS,
        "best_epoch": best_epoch,
        "best_validation_loss": best_validation_loss,
        "best_metrics": {
            k: {mk: round(float(mv), 6) for mk, mv in v.items()}
            for k, v in best_metrics.items()
        },
        "history": history
    }

    with open(METRICS_PATH, "w") as mf:
        json.dump(summary_data, mf, indent=2)

    print("\n" + "=" * 85)
    print("EXPERIMENT 2 TRAINING COMPLETE")
    print(f"Total Epochs: {EPOCHS} | Best Epoch: {best_epoch} | Best Val Loss: {best_validation_loss:.6f}")
    print(f"Checkpoint saved: {CHECKPOINT_PATH}")
    print("=" * 85)


if __name__ == "__main__":
    main()
