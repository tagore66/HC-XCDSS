"""
HC-XCDSS Experiment 1: Rigorous Evaluation & Comparative Benchmark

Compares:
- Baseline Model (224x224, No Augmentation, Epoch 3, best_densenet121_balanced.pth)
- Experiment 1 Model (320x320, Radiographic Augmentation, 8 Epochs, densenet121_320_aug_best.pth)

Produces:
- ROC-AUC, PR-AUC, Precision, Recall/Sensitivity, Specificity, F1
- Thresholds
- Confusion matrices
- Side-by-side delta comparison table
"""

import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from torchvision import transforms
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
    roc_curve,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "src" / "data"))
sys.path.append(str(PROJECT_ROOT / "src" / "models"))
sys.path.append(str(PROJECT_ROOT / "src" / "evaluation"))

from dataset import CheXpertDataset
from densenet import CheXpertDenseNet

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
VALIDATION_CSV = str(PROJECT_ROOT / "data" / "splits" / "validation_clean.csv")

BASELINE_CKPT = PROJECT_ROOT / "models" / "checkpoints" / "best_densenet121_balanced.pth"
EXP1_CKPT = PROJECT_ROOT / "models" / "checkpoints" / "densenet121_320_aug_best.pth"
REPORT_PATH = PROJECT_ROOT / "outputs" / "evaluation" / "experiment1_comparison_report.json"

TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]


def evaluate_model_on_val(ckpt_path, resolution, batch_size=16):
    print(f"\nEvaluating: {ckpt_path.name} (Resolution: {resolution}x{resolution})")
    transform = transforms.Compose([
        transforms.Resize((resolution, resolution)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

    val_dataset = CheXpertDataset(VALIDATION_CSV, transform=transform)
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=2 if DEVICE.type == "cuda" else 0,
        pin_memory=(DEVICE.type == "cuda")
    )

    model = CheXpertDenseNet(num_classes=5).to(DEVICE)
    ckpt = torch.load(ckpt_path, map_location=DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    all_preds = []
    all_targets = []
    all_masks = []

    with torch.no_grad():
        for images, labels, masks in val_loader:
            images = images.to(DEVICE, non_blocking=True)
            outputs = model(images)
            probs = torch.sigmoid(outputs)

            all_preds.append(probs.cpu().numpy())
            all_targets.append(labels.cpu().numpy())
            all_masks.append(masks.cpu().numpy())

    all_preds = np.concatenate(all_preds, axis=0)
    all_targets = np.concatenate(all_targets, axis=0)
    all_masks = np.concatenate(all_masks, axis=0)

    results = {}

    for idx, target in enumerate(TARGETS):
        valid = all_masks[:, idx].astype(bool)
        y_true = all_targets[valid, idx]
        y_score = all_preds[valid, idx]

        total_valid = len(y_true)
        positives = int(np.sum(y_true == 1))
        negatives = int(np.sum(y_true == 0))

        if len(np.unique(y_true)) < 2:
            continue

        roc_auc = roc_auc_score(y_true, y_score)
        pr_auc = average_precision_score(y_true, y_score)

        # Compute optimal threshold using Youden's J statistic
        fpr, tpr, thresholds = roc_curve(y_true, y_score)
        j_scores = tpr - fpr
        best_j_idx = np.argmax(j_scores)
        optimal_threshold = float(thresholds[best_j_idx])
        # Clip threshold to valid [0.05, 0.95] range
        optimal_threshold = max(0.05, min(0.95, optimal_threshold))

        # Metrics at optimal threshold
        y_pred = (y_score >= optimal_threshold).astype(int)
        precision = precision_score(y_true, y_pred, zero_division=0)
        sensitivity = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

        results[target] = {
            "samples": total_valid,
            "positives": positives,
            "negatives": negatives,
            "optimal_threshold": round(optimal_threshold, 4),
            "ROC_AUC": round(float(roc_auc), 4),
            "PR_AUC": round(float(pr_auc), 4),
            "Precision": round(float(precision), 4),
            "Sensitivity": round(float(sensitivity), 4),
            "Specificity": round(float(specificity), 4),
            "F1": round(float(f1), 4),
            "TP": int(tp),
            "FP": int(fp),
            "TN": int(tn),
            "FN": int(fn),
        }

    return results, ckpt.get("epoch"), ckpt.get("validation_loss")


def main():
    print("=" * 80)
    print("HC-XCDSS EXPERIMENT 1 COMPARATIVE BENCHMARK")
    print("=" * 80)

    # 1. Evaluate Baseline Model
    baseline_results, base_epoch, base_loss = evaluate_model_on_val(
        BASELINE_CKPT, resolution=224
    )

    # 2. Evaluate Experiment 1 Model
    exp1_results, exp1_epoch, exp1_loss = evaluate_model_on_val(
        EXP1_CKPT, resolution=320
    )

    # 3. Print Comprehensive Comparison Table
    print("\n" + "=" * 105)
    print(f"{'Finding':<18} | {'Metric':<12} | {'Baseline (224x224, Ep3)':<24} | {'Exp 1 (320x320, 8 Ep)':<22} | {'Delta':<10} | {'Status':<8}")
    print("=" * 105)

    comparison_data = {}

    for target in TARGETS:
        b = baseline_results[target]
        e = exp1_results[target]

        auc_diff = e["ROC_AUC"] - b["ROC_AUC"]
        f1_diff = e["F1"] - b["F1"]
        pr_diff = e["PR_AUC"] - b["PR_AUC"]
        sens_diff = e["Sensitivity"] - b["Sensitivity"]
        spec_diff = e["Specificity"] - b["Specificity"]

        status = "IMPROVED" if (auc_diff >= 0 and f1_diff >= 0) else ("MIXED" if (auc_diff >= 0 or f1_diff >= 0) else "DECLINED")

        comparison_data[target] = {
            "baseline": b,
            "experiment1": e,
            "deltas": {
                "ROC_AUC": round(auc_diff, 4),
                "PR_AUC": round(pr_diff, 4),
                "F1": round(f1_diff, 4),
                "Sensitivity": round(sens_diff, 4),
                "Specificity": round(spec_diff, 4)
            },
            "status": status
        }

        print(f"{target:<18} | {'ROC-AUC':<12} | {b['ROC_AUC']:<24.4f} | {e['ROC_AUC']:<22.4f} | {auc_diff:+<10.4f} | {status:<8}")
        print(f"{'':<18} | {'PR-AUC':<12} | {b['PR_AUC']:<24.4f} | {e['PR_AUC']:<22.4f} | {pr_diff:+<10.4f} |")
        print(f"{'':<18} | {'F1':<12} | {b['F1']:<24.4f} | {e['F1']:<22.4f} | {f1_diff:+<10.4f} |")
        print(f"{'':<18} | {'Sensitivity':<12} | {b['Sensitivity']:<24.4f} | {e['Sensitivity']:<22.4f} | {sens_diff:+<10.4f} |")
        print(f"{'':<18} | {'Specificity':<12} | {b['Specificity']:<24.4f} | {e['Specificity']:<22.4f} | {spec_diff:+<10.4f} |")
        print(f"{'':<18} | {'Threshold':<12} | {b['optimal_threshold']:<24.4f} | {e['optimal_threshold']:<22.4f} | {'—':<10} |")
        print("-" * 105)

    full_report = {
        "baseline_model": {
            "checkpoint": str(BASELINE_CKPT),
            "epoch": base_epoch,
            "validation_loss": round(float(base_loss), 6) if base_loss else None,
            "resolution": 224,
            "metrics": baseline_results
        },
        "experiment1_model": {
            "checkpoint": str(EXP1_CKPT),
            "epoch": exp1_epoch,
            "validation_loss": round(float(exp1_loss), 6) if exp1_loss else None,
            "resolution": 320,
            "metrics": exp1_results
        },
        "comparison": comparison_data
    }

    with open(REPORT_PATH, "w") as rf:
        json.dump(full_report, rf, indent=2)

    print(f"\nFull comparison report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
