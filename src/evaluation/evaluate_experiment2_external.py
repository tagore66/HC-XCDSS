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
# Paths & Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "src" / "models"))
from densenet import CheXpertDenseNet

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

IMAGE_DIRECTORY = PROJECT_ROOT / "external_test" / "images"
LABELS_CSV = PROJECT_ROOT / "external_test" / "labels.csv"

BASELINE_CHECKPOINT_PATH = PROJECT_ROOT / "models" / "checkpoints" / "best_densenet121_balanced.pth"
EXP2_CHECKPOINT_PATH = PROJECT_ROOT / "models" / "checkpoints" / "densenet121_320_noaug_best.pth"
THRESHOLD_PATH = PROJECT_ROOT / "models" / "checkpoints" / "optimal_thresholds_balanced.json"

OUTPUT_DIRECTORY = PROJECT_ROOT / "outputs" / "evaluation"
OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

CSV_OUTPUT_PATH = OUTPUT_DIRECTORY / "external_validation_exp2_comparison.csv"
JSON_OUTPUT_PATH = OUTPUT_DIRECTORY / "external_validation_exp2_comparison.json"

TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]

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
    model = CheXpertDenseNet(num_classes=5).to(DEVICE)
    ckpt = torch.load(checkpoint_path, map_location=DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model, ckpt.get("epoch")


def run_inference(model, transform, df):
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
    print("HC-XCDSS EXTERNAL VALIDATION: BASELINE vs. EXPERIMENT 2 COMPARISON")
    print("=" * 85)
    print(f"Device: {DEVICE}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    if not LABELS_CSV.exists():
        print(f"ERROR: labels.csv not found: {LABELS_CSV}")
        sys.exit(1)

    if not IMAGE_DIRECTORY.exists():
        print(f"ERROR: External image directory not found: {IMAGE_DIRECTORY}")
        sys.exit(1)

    if not BASELINE_CHECKPOINT_PATH.exists():
        print(f"ERROR: Baseline checkpoint not found: {BASELINE_CHECKPOINT_PATH}")
        sys.exit(1)

    if not EXP2_CHECKPOINT_PATH.exists():
        print(f"ERROR: Experiment 2 checkpoint not found: {EXP2_CHECKPOINT_PATH}")
        sys.exit(1)

    if not THRESHOLD_PATH.exists():
        print(f"ERROR: Thresholds not found: {THRESHOLD_PATH}")
        sys.exit(1)

    df = pd.read_csv(LABELS_CSV)
    with open(THRESHOLD_PATH, "r") as f:
        thresholds = json.load(f)

    print(f"\nExternal Test Images in Dataset: {len(df)}")
    print("Fixed Operating Thresholds:")
    for t in TARGETS:
        print(f"  - {t:<18}: {thresholds[t]:.4f}")

    # 1. Baseline Model Inference (224x224)
    print("\nRunning Baseline Model Inference (224x224)...")
    baseline_model, baseline_epoch = load_model(BASELINE_CHECKPOINT_PATH)
    baseline_probs, valid_idx_base, skipped_base = run_inference(baseline_model, TRANSFORM_224, df)
    del baseline_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # 2. Experiment 2 Model Inference (320x320)
    print("Running Experiment 2 Model Inference (320x320, NoAug)...")
    exp2_model, exp2_epoch = load_model(EXP2_CHECKPOINT_PATH)
    exp2_probs, valid_idx_exp2, skipped_exp2 = run_inference(exp2_model, TRANSFORM_320, df)
    del exp2_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    common_indices = [idx for idx in valid_idx_base if idx in valid_idx_exp2]
    df_valid = df.loc[common_indices].reset_index(drop=True)

    detailed_records = []
    baseline_findings_metrics = {}
    exp2_findings_metrics = {}
    comparison_summary = {}

    confirmed_changes = []
    unknown_changes = []

    for t_idx, target in enumerate(TARGETS):
        thresh = float(thresholds[target])
        y_all = df_valid[target].to_numpy(dtype=int)
        base_p_all = baseline_probs[:, t_idx]
        exp2_p_all = exp2_probs[:, t_idx]

        valid_mask = (y_all != -1)
        y_valid = y_all[valid_mask]
        base_p_valid = base_p_all[valid_mask]
        exp2_p_valid = exp2_p_all[valid_mask]
        unknown_count = int((~valid_mask).sum())

        base_m = calculate_metrics_for_target(y_valid, base_p_valid, thresh)
        base_m["unknown_labels"] = unknown_count
        baseline_findings_metrics[target] = base_m

        exp2_m = calculate_metrics_for_target(y_valid, exp2_p_valid, thresh)
        exp2_m["unknown_labels"] = unknown_count
        exp2_findings_metrics[target] = exp2_m

        for img_idx, row in df_valid.iterrows():
            gt = int(row[target])
            bp = float(base_p_all[img_idx])
            ep = float(exp2_p_all[img_idx])
            b_pred = int(bp >= thresh)
            e_pred = int(ep >= thresh)

            rec = {
                "image": str(row["image"]),
                "finding": target,
                "ground_truth": gt,
                "baseline_probability": round(bp, 6),
                "experiment2_probability": round(ep, 6),
                "baseline_prediction": b_pred,
                "experiment2_prediction": e_pred,
                "prediction_changed": bool(b_pred != e_pred)
            }
            detailed_records.append(rec)

            if b_pred != e_pred:
                if gt != -1:
                    confirmed_changes.append(rec)
                else:
                    unknown_changes.append(rec)

        auc_delta = None
        if exp2_m["ROC_AUC"] is not None and base_m["ROC_AUC"] is not None:
            auc_delta = round(exp2_m["ROC_AUC"] - base_m["ROC_AUC"], 4)

        comparison_summary[target] = {
            "threshold": thresh,
            "valid_ground_truth_images": base_m["valid_ground_truth_images"],
            "unknown_labels": unknown_count,
            "baseline": base_m,
            "experiment2": exp2_m,
            "deltas": {
                "ROC_AUC": auc_delta,
                "Sensitivity": round(exp2_m["Sensitivity"] - base_m["Sensitivity"], 4),
                "Specificity": round(exp2_m["Specificity"] - base_m["Specificity"], 4),
                "Precision": round(exp2_m["Precision"] - base_m["Precision"], 4),
                "F1": round(exp2_m["F1"] - base_m["F1"], 4)
            }
        }

    # Save CSV
    comparison_df = pd.DataFrame(detailed_records)
    comparison_df.to_csv(CSV_OUTPUT_PATH, index=False)
    print(f"\nPer-image comparison saved: {CSV_OUTPUT_PATH}")

    # Save JSON
    full_json_report = {
        "dataset": "external_test",
        "total_images": len(df_valid),
        "baseline_model": {
            "checkpoint": str(BASELINE_CHECKPOINT_PATH),
            "epoch": baseline_epoch,
            "resolution": (224, 224),
            "metrics": baseline_findings_metrics
        },
        "experiment2_model": {
            "checkpoint": str(EXP2_CHECKPOINT_PATH),
            "epoch": exp2_epoch,
            "resolution": (320, 320),
            "metrics": exp2_findings_metrics
        },
        "findings_comparison": comparison_summary,
        "prediction_changes_summary": {
            "total_evaluations": len(detailed_records),
            "total_changes": len(confirmed_changes) + len(unknown_changes),
            "confirmed_label_changes_count": len(confirmed_changes),
            "unknown_label_changes_count": len(unknown_changes),
            "confirmed_label_changes": confirmed_changes,
            "unknown_label_changes": unknown_changes
        },
        "detailed_predictions": detailed_records
    }

    with open(JSON_OUTPUT_PATH, "w") as f:
        json.dump(full_json_report, f, indent=4)
    print(f"Summary comparison JSON saved: {JSON_OUTPUT_PATH}")

    # Print Table
    print("\n" + "=" * 105)
    print("HC-XCDSS EXTERNAL VALIDATION: BASELINE vs. EXPERIMENT 2 PERFORMANCE")
    print("=" * 105)
    header = f"{'Finding':<18} | {'Metric':<12} | {'Baseline (224x224)':<20} | {'Exp 2 (320x320)':<20} | {'Delta':<10}"
    print(header)
    print("-" * 105)

    for target in TARGETS:
        b = baseline_findings_metrics[target]
        e = exp2_findings_metrics[target]
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
    print(f"PREDICTION CHANGES BREAKDOWN (Total Evaluations: {len(detailed_records)})")
    print(f"  - Confirmed Ground-Truth Label Changes: {len(confirmed_changes)}")
    print(f"  - Unknown Ground-Truth (-1) Label Changes: {len(unknown_changes)}")
    print("=" * 105)

    if confirmed_changes:
        print("\nConfirmed Ground-Truth Disagreements:")
        for c in confirmed_changes:
            print(f"  - Image: {c['image']:<28} | Finding: {c['finding']:<16} | GT: {c['ground_truth']} | Base Prob: {c['baseline_probability']:.4f} (pred {c['baseline_prediction']}) -> Exp2 Prob: {c['experiment2_probability']:.4f} (pred {c['experiment2_prediction']})")

    print("\n" + "=" * 105)
    print("EXTERNAL VALIDATION EXP2 BENCHMARK COMPLETE")
    print("=" * 105)


if __name__ == "__main__":
    main()
