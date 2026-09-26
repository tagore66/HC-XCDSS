"""
HC-XCDSS Experiment 2: Evaluation on Internal Validation Split

Evaluates:
- Experiment 2 (320x320, NO Augmentation, densenet121_320_noaug_best.pth)
Against:
- Baseline (224x224, best_densenet121_balanced.pth)
- Experiment 1 (320x320 + Augmentation, densenet121_320_aug_best.pth)

Produces:
- ROC-AUC, PR-AUC, Precision, Recall/Sensitivity, Specificity, F1
- Optimal thresholds
- Comparison report in outputs/evaluation/experiment2_comparison_report.json
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
EXP2_CKPT = PROJECT_ROOT / "models" / "checkpoints" / "densenet121_320_noaug_best.pth"
REPORT_PATH = PROJECT_ROOT / "outputs" / "evaluation" / "experiment2_comparison_report.json"

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

        fpr, tpr, thresholds = roc_curve(y_true, y_score)
        j_scores = tpr - fpr
        best_j_idx = np.argmax(j_scores)
        optimal_threshold = float(thresholds[best_j_idx])
        optimal_threshold = max(0.05, min(0.95, optimal_threshold))

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
    print("=" * 85)
    print("HC-XCDSS EXPERIMENT 2 BENCHMARK ON INTERNAL VALIDATION SPLIT")
    print("=" * 85)

    # 1. Baseline
    baseline_results, base_epoch, base_loss = evaluate_model_on_val(
        BASELINE_CKPT, resolution=224
    )

    # 2. Experiment 2
    exp2_results, exp2_epoch, exp2_loss = evaluate_model_on_val(
        EXP2_CKPT, resolution=320
    )

    # Print Table
    print("\n" + "=" * 110)
    print(f"{'Finding':<18} | {'Metric':<12} | {'Baseline (224x224)':<22} | {'Exp 2 (320x320, NoAug)':<24} | {'Delta':<10}")
    print("=" * 110)

    comparison_data = {}

    for target in TARGETS:
        b = baseline_results[target]
        e2 = exp2_results[target]

        auc_diff = e2["ROC_AUC"] - b["ROC_AUC"]
        pr_diff = e2["PR_AUC"] - b["PR_AUC"]
        f1_diff = e2["F1"] - b["F1"]
        sens_diff = e2["Sensitivity"] - b["Sensitivity"]
        spec_diff = e2["Specificity"] - b["Specificity"]

        comparison_data[target] = {
            "baseline": b,
            "experiment2": e2,
            "deltas": {
                "ROC_AUC": round(auc_diff, 4),
                "PR_AUC": round(pr_diff, 4),
                "F1": round(f1_diff, 4),
                "Sensitivity": round(sens_diff, 4),
                "Specificity": round(spec_diff, 4)
            }
        }

        print(f"{target:<18} | {'ROC-AUC':<12} | {b['ROC_AUC']:<22.4f} | {e2['ROC_AUC']:<24.4f} | {auc_diff:+<10.4f}")
        print(f"{'':<18} | {'PR-AUC':<12} | {b['PR_AUC']:<22.4f} | {e2['PR_AUC']:<24.4f} | {pr_diff:+<10.4f}")
        print(f"{'':<18} | {'Sensitivity':<12} | {b['Sensitivity']:<22.4f} | {e2['Sensitivity']:<24.4f} | {sens_diff:+<10.4f}")
        print(f"{'':<18} | {'Specificity':<12} | {b['Specificity']:<22.4f} | {e2['Specificity']:<24.4f} | {spec_diff:+<10.4f}")
        print(f"{'':<18} | {'Precision':<12} | {b['Precision']:<22.4f} | {e2['Precision']:<24.4f} | {e2['Precision'] - b['Precision']:+<10.4f}")
        print(f"{'':<18} | {'F1':<12} | {b['F1']:<22.4f} | {e2['F1']:<24.4f} | {f1_diff:+<10.4f}")
        print(f"{'':<18} | {'Threshold':<12} | {b['optimal_threshold']:<22.4f} | {e2['optimal_threshold']:<24.4f} | {'—':<10}")
        print("-" * 110)

    # Macro Averages
    macro_base = {
        "ROC_AUC": round(float(np.mean([baseline_results[t]["ROC_AUC"] for t in TARGETS])), 4),
        "PR_AUC": round(float(np.mean([baseline_results[t]["PR_AUC"] for t in TARGETS])), 4),
        "Sensitivity": round(float(np.mean([baseline_results[t]["Sensitivity"] for t in TARGETS])), 4),
        "Specificity": round(float(np.mean([baseline_results[t]["Specificity"] for t in TARGETS])), 4),
        "Precision": round(float(np.mean([baseline_results[t]["Precision"] for t in TARGETS])), 4),
        "F1": round(float(np.mean([baseline_results[t]["F1"] for t in TARGETS])), 4)
    }

    macro_e2 = {
        "ROC_AUC": round(float(np.mean([exp2_results[t]["ROC_AUC"] for t in TARGETS])), 4),
        "PR_AUC": round(float(np.mean([exp2_results[t]["PR_AUC"] for t in TARGETS])), 4),
        "Sensitivity": round(float(np.mean([exp2_results[t]["Sensitivity"] for t in TARGETS])), 4),
        "Specificity": round(float(np.mean([exp2_results[t]["Specificity"] for t in TARGETS])), 4),
        "Precision": round(float(np.mean([exp2_results[t]["Precision"] for t in TARGETS])), 4),
        "F1": round(float(np.mean([exp2_results[t]["F1"] for t in TARGETS])), 4)
    }

    macro_delta = {k: round(macro_e2[k] - macro_base[k], 4) for k in macro_base}

    print(f"{'MACRO AVERAGE':<18} | {'ROC-AUC':<12} | {macro_base['ROC_AUC']:<22.4f} | {macro_e2['ROC_AUC']:<24.4f} | {macro_delta['ROC_AUC']:+<10.4f}")
    print(f"{'':<18} | {'PR-AUC':<12} | {macro_base['PR_AUC']:<22.4f} | {macro_e2['PR_AUC']:<24.4f} | {macro_delta['PR_AUC']:+<10.4f}")
    print(f"{'':<18} | {'Sensitivity':<12} | {macro_base['Sensitivity']:<22.4f} | {macro_e2['Sensitivity']:<24.4f} | {macro_delta['Sensitivity']:+<10.4f}")
    print(f"{'':<18} | {'Specificity':<12} | {macro_base['Specificity']:<22.4f} | {macro_e2['Specificity']:<24.4f} | {macro_delta['Specificity']:+<10.4f}")
    print(f"{'':<18} | {'Precision':<12} | {macro_base['Precision']:<22.4f} | {macro_e2['Precision']:<24.4f} | {macro_delta['Precision']:+<10.4f}")
    print(f"{'':<18} | {'F1':<12} | {macro_base['F1']:<22.4f} | {macro_e2['F1']:<24.4f} | {macro_delta['F1']:+<10.4f}")
    print("=" * 110)

    full_report = {
        "baseline_model": {
            "checkpoint": str(BASELINE_CKPT),
            "epoch": base_epoch,
            "validation_loss": round(float(base_loss), 6) if base_loss else None,
            "resolution": 224,
            "metrics": baseline_results,
            "macro_averages": macro_base
        },
        "experiment2_model": {
            "checkpoint": str(EXP2_CKPT),
            "epoch": exp2_epoch,
            "validation_loss": round(float(exp2_loss), 6) if exp2_loss else None,
            "resolution": 320,
            "metrics": exp2_results,
            "macro_averages": macro_e2
        },
        "comparison": comparison_data,
        "macro_deltas": macro_delta
    }

    with open(REPORT_PATH, "w") as rf:
        json.dump(full_report, rf, indent=2)

    print(f"\nReport saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
