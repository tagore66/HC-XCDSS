import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torchvision import transforms
from sklearn.metrics import (
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score
)

# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "src" / "models"))

from densenet import CheXpertDenseNet

# ============================================================
# Configuration
# ============================================================

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

IMAGE_DIRECTORY = PROJECT_ROOT / "external_test" / "images"
LABELS_CSV = PROJECT_ROOT / "external_test" / "labels.csv"

BASELINE_CHECKPOINT_PATH = PROJECT_ROOT / "models" / "checkpoints" / "best_densenet121_balanced.pth"
EXP1_CHECKPOINT_PATH = PROJECT_ROOT / "models" / "checkpoints" / "densenet121_320_aug_best.pth"
THRESHOLD_PATH = PROJECT_ROOT / "models" / "checkpoints" / "optimal_thresholds_balanced.json"

OUTPUT_DIRECTORY = PROJECT_ROOT / "outputs" / "evaluation"
OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

CSV_OUTPUT_PATH = OUTPUT_DIRECTORY / "external_validation_comparison.csv"
JSON_OUTPUT_PATH = OUTPUT_DIRECTORY / "external_validation_comparison.json"

TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]

# ============================================================
# Preprocessing Transforms
# ============================================================

TRANSFORM_224 = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

TRANSFORM_320 = transforms.Compose([
    transforms.Resize((320, 320)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


def load_model(checkpoint_path):
    """Load DenseNet121 model from checkpoint."""
    model = CheXpertDenseNet(num_classes=5).to(DEVICE)
    ckpt = torch.load(checkpoint_path, map_location=DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model, ckpt.get("epoch")


def run_inference(model, transform, df):
    """Run inference over external images dataframe and return probabilities array and valid indices."""
    probabilities_list = []
    valid_indices = []
    skipped = 0

    for idx, row in df.iterrows():
        image_name = str(row["image"])
        image_path = IMAGE_DIRECTORY / image_name

        if not image_path.exists():
            print(f"  WARNING: Image not found: {image_path}")
            skipped += 1
            continue

        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as err:
            print(f"  WARNING: Could not read {image_path}: {err}")
            skipped += 1
            continue

        tensor = transform(image).unsqueeze(0).to(DEVICE)

        with torch.inference_mode():
            outputs = model(tensor)
            probs = torch.sigmoid(outputs)[0].cpu().numpy()

        probabilities_list.append(probs)
        valid_indices.append(idx)

    return np.array(probabilities_list), valid_indices, skipped


def calculate_metrics_for_target(y_true, y_scores, threshold):
    """Calculate clinical classification and ranking metrics for a specific target."""
    total_valid = len(y_true)
    if total_valid == 0:
        return {
            "status": "no_ground_truth",
            "valid_ground_truth_images": 0,
            "threshold": threshold,
            "ROC_AUC": None,
            "Sensitivity": None,
            "Specificity": None,
            "Precision": None,
            "F1": None,
            "TP": 0,
            "TN": 0,
            "FP": 0,
            "FN": 0
        }

    # ROC-AUC calculation
    if len(np.unique(y_true)) >= 2:
        roc_auc = float(roc_auc_score(y_true, y_scores))
    else:
        roc_auc = None

    y_pred = (y_scores >= threshold).astype(int)

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    sensitivity = float(recall_score(y_true, y_pred, zero_division=0))
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    precision = float(precision_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    return {
        "status": "evaluated",
        "valid_ground_truth_images": int(total_valid),
        "threshold": float(threshold),
        "ROC_AUC": round(roc_auc, 4) if roc_auc is not None else None,
        "Sensitivity": round(sensitivity, 4),
        "Specificity": round(specificity, 4),
        "Precision": round(precision, 4),
        "F1": round(f1, 4),
        "TP": int(tp),
        "TN": int(tn),
        "FP": int(fp),
        "FN": int(fn)
    }


def main():
    print("=" * 85)
    print("HC-XCDSS EXTERNAL VALIDATION: BASELINE vs. EXPERIMENT 1 COMPARISON")
    print("=" * 85)
    print(f"Device: {DEVICE}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    # Validate Files
    if not LABELS_CSV.exists():
        print(f"ERROR: labels.csv not found: {LABELS_CSV}")
        sys.exit(1)

    if not IMAGE_DIRECTORY.exists():
        print(f"ERROR: External image directory not found: {IMAGE_DIRECTORY}")
        sys.exit(1)

    if not BASELINE_CHECKPOINT_PATH.exists():
        print(f"ERROR: Baseline checkpoint not found: {BASELINE_CHECKPOINT_PATH}")
        sys.exit(1)

    if not EXP1_CHECKPOINT_PATH.exists():
        print(f"ERROR: Experiment 1 checkpoint not found: {EXP1_CHECKPOINT_PATH}")
        sys.exit(1)

    if not THRESHOLD_PATH.exists():
        print(f"ERROR: Thresholds not found: {THRESHOLD_PATH}")
        sys.exit(1)

    # Load Labels
    df = pd.read_csv(LABELS_CSV)
    required_columns = ["image", *TARGETS]
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        print(f"ERROR: Missing columns in labels.csv: {missing}")
        sys.exit(1)

    # Load Fixed Thresholds
    with open(THRESHOLD_PATH, "r") as f:
        thresholds = json.load(f)

    print(f"\nExternal Test Images in Dataset: {len(df)}")
    print("Configured Fixed Operating Thresholds:")
    for t in TARGETS:
        print(f"  - {t:<18}: {thresholds[t]:.4f}")

    # 1. Baseline Model Inference (224x224)
    print("\n" + "-" * 60)
    print(f"Running Baseline Model Inference (224x224)...")
    print(f"Checkpoint: {BASELINE_CHECKPOINT_PATH.name}")
    print("-" * 60)
    baseline_model, baseline_epoch = load_model(BASELINE_CHECKPOINT_PATH)
    baseline_probs, valid_idx_base, skipped_base = run_inference(baseline_model, TRANSFORM_224, df)
    del baseline_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # 2. Experiment 1 Model Inference (320x320)
    print("\n" + "-" * 60)
    print(f"Running Experiment 1 Model Inference (320x320)...")
    print(f"Checkpoint: {EXP1_CHECKPOINT_PATH.name}")
    print("-" * 60)
    exp1_model, exp1_epoch = load_model(EXP1_CHECKPOINT_PATH)
    exp1_probs, valid_idx_exp1, skipped_exp1 = run_inference(exp1_model, TRANSFORM_320, df)
    del exp1_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    if len(baseline_probs) == 0 or len(exp1_probs) == 0:
        print("ERROR: No valid images processed.")
        sys.exit(1)

    # Align on common valid images
    common_indices = [idx for idx in valid_idx_base if idx in valid_idx_exp1]
    df_valid = df.loc[common_indices].reset_index(drop=True)

    # 3. Collect Per-Image, Per-Finding Records
    detailed_records = []
    baseline_findings_metrics = {}
    exp1_findings_metrics = {}
    comparison_summary = {}

    for t_idx, target in enumerate(TARGETS):
        thresh = float(thresholds[target])
        y_all = df_valid[target].to_numpy(dtype=int)
        base_p_all = baseline_probs[:, t_idx]
        exp1_p_all = exp1_probs[:, t_idx]

        # Valid mask (exclude -1)
        valid_mask = (y_all != -1)
        y_valid = y_all[valid_mask]
        base_p_valid = base_p_all[valid_mask]
        exp1_p_valid = exp1_p_all[valid_mask]
        unknown_count = int((~valid_mask).sum())

        # Metrics
        base_m = calculate_metrics_for_target(y_valid, base_p_valid, thresh)
        base_m["unknown_labels"] = unknown_count
        baseline_findings_metrics[target] = base_m

        exp1_m = calculate_metrics_for_target(y_valid, exp1_p_valid, thresh)
        exp1_m["unknown_labels"] = unknown_count
        exp1_findings_metrics[target] = exp1_m

        # Per-image rows
        for img_idx, row in df_valid.iterrows():
            gt = int(row[target])
            bp = float(base_p_all[img_idx])
            ep = float(exp1_p_all[img_idx])
            b_pred = int(bp >= thresh)
            e_pred = int(ep >= thresh)

            detailed_records.append({
                "image": str(row["image"]),
                "finding": target,
                "ground_truth": gt,
                "baseline_probability": round(bp, 6),
                "experiment1_probability": round(ep, 6),
                "baseline_prediction": b_pred,
                "experiment1_prediction": e_pred
            })

        # Calculate deltas
        auc_delta = None
        if exp1_m["ROC_AUC"] is not None and base_m["ROC_AUC"] is not None:
            auc_delta = round(exp1_m["ROC_AUC"] - base_m["ROC_AUC"], 4)

        comparison_summary[target] = {
            "threshold": thresh,
            "valid_ground_truth_images": base_m["valid_ground_truth_images"],
            "unknown_labels": unknown_count,
            "baseline": base_m,
            "experiment1": exp1_m,
            "deltas": {
                "ROC_AUC": auc_delta,
                "Sensitivity": round(exp1_m["Sensitivity"] - base_m["Sensitivity"], 4),
                "Specificity": round(exp1_m["Specificity"] - base_m["Specificity"], 4),
                "Precision": round(exp1_m["Precision"] - base_m["Precision"], 4),
                "F1": round(exp1_m["F1"] - base_m["F1"], 4)
            }
        }

    # 4. Save CSV Comparison
    comparison_df = pd.DataFrame(detailed_records)
    comparison_df.to_csv(CSV_OUTPUT_PATH, index=False)
    print(f"\nPer-image comparison saved: {CSV_OUTPUT_PATH}")

    # 5. Save JSON Comparison
    full_json_report = {
        "dataset": "external_test",
        "total_images": len(df_valid),
        "baseline_model": {
            "checkpoint": str(BASELINE_CHECKPOINT_PATH),
            "epoch": baseline_epoch,
            "resolution": (224, 224),
            "metrics": baseline_findings_metrics
        },
        "experiment1_model": {
            "checkpoint": str(EXP1_CHECKPOINT_PATH),
            "epoch": exp1_epoch,
            "resolution": (320, 320),
            "metrics": exp1_findings_metrics
        },
        "findings_comparison": comparison_summary,
        "detailed_predictions": detailed_records
    }

    with open(JSON_OUTPUT_PATH, "w") as f:
        json.dump(full_json_report, f, indent=4)
    print(f"Summary comparison JSON saved: {JSON_OUTPUT_PATH}")

    # 6. Print Terminal Comparison Table
    print("\n" + "=" * 105)
    print("HC-XCDSS EXTERNAL VALIDATION: BASELINE vs. EXPERIMENT 1 PERFORMANCE")
    print("=" * 105)
    header = f"{'Finding':<18} | {'Metric':<12} | {'Baseline (224x224)':<20} | {'Exp 1 (320x320)':<20} | {'Delta':<10}"
    print(header)
    print("-" * 105)

    for target in TARGETS:
        b = baseline_findings_metrics[target]
        e = exp1_findings_metrics[target]
        d = comparison_summary[target]["deltas"]

        b_auc_str = f"{b['ROC_AUC']:.4f}" if b['ROC_AUC'] is not None else "N/A"
        e_auc_str = f"{e['ROC_AUC']:.4f}" if e['ROC_AUC'] is not None else "N/A"
        d_auc_str = f"{d['ROC_AUC']:+.4f}" if d['ROC_AUC'] is not None else "N/A"

        print(f"{target:<18} | {'ROC-AUC':<12} | {b_auc_str:<20} | {e_auc_str:<20} | {d_auc_str:<10}")
        print(f"{'':<18} | {'Sensitivity':<12} | {b['Sensitivity']:<20.4f} | {e['Sensitivity']:<20.4f} | {d['Sensitivity']:+<10.4f}")
        print(f"{'':<18} | {'Specificity':<12} | {b['Specificity']:<20.4f} | {e['Specificity']:<20.4f} | {d['Specificity']:+<10.4f}")
        print(f"{'':<18} | {'Precision':<12} | {b['Precision']:<20.4f} | {e['Precision']:<20.4f} | {d['Precision']:+<10.4f}")
        print(f"{'':<18} | {'F1':<12} | {b['F1']:<20.4f} | {e['F1']:<20.4f} | {d['F1']:+<10.4f}")
        print(f"{'':<18} | {'TP / FP / FN':<12} | {b['TP']}/{b['FP']}/{b['FN']:<15} | {e['TP']}/{e['FP']}/{e['FN']:<15} | {'—':<10}")
        print(f"{'':<18} | {'Valid / Unknown':<12} | {b['valid_ground_truth_images']}/{b['unknown_labels']:<15} | {e['valid_ground_truth_images']}/{e['unknown_labels']:<15} | {'—':<10}")
        print("-" * 105)

    print("\n" + "=" * 105)
    print("EXTERNAL VALIDATION COMPARISON COMPLETE")
    print("=" * 105)


if __name__ == "__main__":
    main()