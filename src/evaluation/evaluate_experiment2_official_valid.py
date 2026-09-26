import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torchvision import transforms
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)

# ============================================================
# Paths & Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "src" / "models"))
from densenet import CheXpertDenseNet

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

VALID_CSV = PROJECT_ROOT / "data" / "valid.csv"
DATA_DIR = PROJECT_ROOT / "data"

BASELINE_CKPT = PROJECT_ROOT / "models" / "checkpoints" / "best_densenet121_balanced.pth"
EXP2_CKPT = PROJECT_ROOT / "models" / "checkpoints" / "densenet121_320_noaug_best.pth"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "evaluation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JSON_OUTPUT_PATH = OUTPUT_DIR / "official_valid_experiment2.json"
CSV_OUTPUT_PATH = OUTPUT_DIR / "official_valid_experiment2.csv"

TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]

BASELINE_THRESHOLDS = {
    "Atelectasis": 0.3377,
    "Cardiomegaly": 0.5939,
    "Consolidation": 0.4962,
    "Edema": 0.4999,
    "Pleural Effusion": 0.5009
}

EXP2_THRESHOLDS = {
    "Atelectasis": 0.4189,
    "Cardiomegaly": 0.5407,
    "Consolidation": 0.3573,
    "Edema": 0.5251,
    "Pleural Effusion": 0.4538
}

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
        rel_path = str(row["Path"]).replace("CheXpert-v1.0-small/", "")
        img_path = DATA_DIR / rel_path

        if not img_path.exists():
            print(f"  WARNING: Image not found: {img_path}")
            skipped += 1
            continue

        try:
            image = Image.open(img_path).convert("RGB")
        except Exception as err:
            print(f"  WARNING: Could not read {img_path}: {err}")
            skipped += 1
            continue

        tensor = transform(image).unsqueeze(0).to(DEVICE)

        with torch.inference_mode():
            outputs = model(tensor)
            probs = torch.sigmoid(outputs)[0].cpu().numpy()

        probabilities_list.append(probs)
        valid_indices.append(idx)

    return np.array(probabilities_list), valid_indices, skipped


def evaluate_predictions(y_true, y_scores, threshold):
    positives = int(np.sum(y_true == 1))
    negatives = int(np.sum(y_true == 0))
    total = len(y_true)

    roc_auc = float(roc_auc_score(y_true, y_scores))
    pr_auc = float(average_precision_score(y_true, y_scores))

    y_pred = (y_scores >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    sensitivity = float(recall_score(y_true, y_pred, zero_division=0))
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    precision = float(precision_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    return {
        "samples": total,
        "positives": positives,
        "negatives": negatives,
        "threshold": round(threshold, 4),
        "ROC_AUC": round(roc_auc, 4),
        "PR_AUC": round(pr_auc, 4),
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
    print("=" * 95)
    print("OFFICIAL CHEXPERT VALIDATION BENCHMARK: BASELINE vs. EXPERIMENT 2 (320x320, NoAug)")
    print("=" * 95)
    print(f"Device: {DEVICE}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    if not VALID_CSV.exists():
        print(f"ERROR: valid.csv not found at {VALID_CSV}")
        sys.exit(1)

    df = pd.read_csv(VALID_CSV)
    print(f"Official Validation Cohort Images: {len(df)}")

    # 1. Baseline Model Inference
    print("\nRunning Baseline Model Inference (224x224)...")
    baseline_model, b_epoch = load_model(BASELINE_CKPT)
    b_probs, b_valid_idx, b_skipped = run_inference(baseline_model, TRANSFORM_224, df)
    del baseline_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # 2. Experiment 2 Model Inference
    print("Running Experiment 2 Model Inference (320x320, NoAug)...")
    exp2_model, e2_epoch = load_model(EXP2_CKPT)
    e2_probs, e2_valid_idx, e2_skipped = run_inference(exp2_model, TRANSFORM_320, df)
    del exp2_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    common_indices = [i for i in b_valid_idx if i in e2_valid_idx]
    df_eval = df.loc[common_indices].reset_index(drop=True)
    total_images_processed = len(df_eval)
    total_skipped = max(b_skipped, e2_skipped)

    print(f"\nSuccessfully Processed Images: {total_images_processed} | Skipped: {total_skipped}")

    baseline_metrics = {}
    exp2_metrics = {}
    findings_comparison = {}
    csv_rows = []

    for t_idx, target in enumerate(TARGETS):
        y_true = df_eval[target].to_numpy(dtype=int)
        b_p = b_probs[:, t_idx]
        e2_p = e2_probs[:, t_idx]

        b_thresh = BASELINE_THRESHOLDS[target]
        e2_thresh = EXP2_THRESHOLDS[target]

        b_res = evaluate_predictions(y_true, b_p, b_thresh)
        e2_res = evaluate_predictions(y_true, e2_p, e2_thresh)

        baseline_metrics[target] = b_res
        exp2_metrics[target] = e2_res

        deltas = {
            "ROC_AUC": round(e2_res["ROC_AUC"] - b_res["ROC_AUC"], 4),
            "PR_AUC": round(e2_res["PR_AUC"] - b_res["PR_AUC"], 4),
            "Sensitivity": round(e2_res["Sensitivity"] - b_res["Sensitivity"], 4),
            "Specificity": round(e2_res["Specificity"] - b_res["Specificity"], 4),
            "Precision": round(e2_res["Precision"] - b_res["Precision"], 4),
            "F1": round(e2_res["F1"] - b_res["F1"], 4),
            "TP": e2_res["TP"] - b_res["TP"],
            "TN": e2_res["TN"] - b_res["TN"],
            "FP": e2_res["FP"] - b_res["FP"],
            "FN": e2_res["FN"] - b_res["FN"]
        }

        findings_comparison[target] = {
            "samples": b_res["samples"],
            "positives": b_res["positives"],
            "negatives": b_res["negatives"],
            "baseline": b_res,
            "experiment2": e2_res,
            "deltas": deltas
        }

        for m_name in ["ROC_AUC", "PR_AUC", "Sensitivity", "Specificity", "Precision", "F1", "threshold", "TP", "TN", "FP", "FN"]:
            csv_rows.append({
                "cohort": "official_chexpert_valid",
                "finding": target,
                "samples": b_res["samples"],
                "positives": b_res["positives"],
                "negatives": b_res["negatives"],
                "metric": m_name,
                "baseline": b_res.get(m_name),
                "experiment2": e2_res.get(m_name),
                "delta_exp2_minus_baseline": deltas.get(m_name, "—")
            })

    # Macro Averages
    macro_baseline = {
        "ROC_AUC": round(float(np.mean([baseline_metrics[t]["ROC_AUC"] for t in TARGETS])), 4),
        "PR_AUC": round(float(np.mean([baseline_metrics[t]["PR_AUC"] for t in TARGETS])), 4),
        "Sensitivity": round(float(np.mean([baseline_metrics[t]["Sensitivity"] for t in TARGETS])), 4),
        "Specificity": round(float(np.mean([baseline_metrics[t]["Specificity"] for t in TARGETS])), 4),
        "Precision": round(float(np.mean([baseline_metrics[t]["Precision"] for t in TARGETS])), 4),
        "F1": round(float(np.mean([baseline_metrics[t]["F1"] for t in TARGETS])), 4)
    }

    macro_exp2 = {
        "ROC_AUC": round(float(np.mean([exp2_metrics[t]["ROC_AUC"] for t in TARGETS])), 4),
        "PR_AUC": round(float(np.mean([exp2_metrics[t]["PR_AUC"] for t in TARGETS])), 4),
        "Sensitivity": round(float(np.mean([exp2_metrics[t]["Sensitivity"] for t in TARGETS])), 4),
        "Specificity": round(float(np.mean([exp2_metrics[t]["Specificity"] for t in TARGETS])), 4),
        "Precision": round(float(np.mean([exp2_metrics[t]["Precision"] for t in TARGETS])), 4),
        "F1": round(float(np.mean([exp2_metrics[t]["F1"] for t in TARGETS])), 4)
    }

    macro_deltas = {
        "ROC_AUC": round(macro_exp2["ROC_AUC"] - macro_baseline["ROC_AUC"], 4),
        "PR_AUC": round(macro_exp2["PR_AUC"] - macro_baseline["PR_AUC"], 4),
        "Sensitivity": round(macro_exp2["Sensitivity"] - macro_baseline["Sensitivity"], 4),
        "Specificity": round(macro_exp2["Specificity"] - macro_baseline["Specificity"], 4),
        "Precision": round(macro_exp2["Precision"] - macro_baseline["Precision"], 4),
        "F1": round(macro_exp2["F1"] - macro_baseline["F1"], 4)
    }

    for m_name in ["ROC_AUC", "PR_AUC", "Sensitivity", "Specificity", "Precision", "F1"]:
        csv_rows.append({
            "cohort": "official_chexpert_valid",
            "finding": "MACRO_AVERAGE",
            "samples": total_images_processed,
            "positives": "—",
            "negatives": "—",
            "metric": m_name,
            "baseline": macro_baseline[m_name],
            "experiment2": macro_exp2[m_name],
            "delta_exp2_minus_baseline": macro_deltas[m_name]
        })

    # Save CSV
    pd.DataFrame(csv_rows).to_csv(CSV_OUTPUT_PATH, index=False)
    print(f"Results CSV saved: {CSV_OUTPUT_PATH}")

    # Save JSON
    full_json = {
        "cohort": "Official CheXpert Radiologist-Consensus Validation Set",
        "csv_path": str(VALID_CSV),
        "images_processed": total_images_processed,
        "images_skipped": total_skipped,
        "baseline_model": {
            "checkpoint": str(BASELINE_CKPT),
            "epoch": b_epoch,
            "resolution": 224,
            "thresholds": BASELINE_THRESHOLDS,
            "metrics": baseline_metrics,
            "macro_averages": macro_baseline
        },
        "experiment2_model": {
            "checkpoint": str(EXP2_CKPT),
            "epoch": e2_epoch,
            "resolution": 320,
            "augmentation": "NONE",
            "thresholds": EXP2_THRESHOLDS,
            "metrics": exp2_metrics,
            "macro_averages": macro_exp2
        },
        "findings_comparison": findings_comparison,
        "macro_deltas": macro_deltas
    }

    with open(JSON_OUTPUT_PATH, "w") as f:
        json.dump(full_json, f, indent=4)
    print(f"Results JSON saved: {JSON_OUTPUT_PATH}")

    # Terminal Comparison Output
    print("\n" + "=" * 110)
    print("OFFICIAL CHEXPERT VALIDATION SET: BASELINE vs. EXPERIMENT 2 PERFORMANCE")
    print("=" * 110)
    print(f"{'Finding':<18} | {'Metric':<14} | {'Baseline (224x224)':<22} | {'Exp 2 (320x320, NoAug)':<24} | {'Delta':<10}")
    print("-" * 110)

    for target in TARGETS:
        b = baseline_metrics[target]
        e2 = exp2_metrics[target]
        d = findings_comparison[target]["deltas"]
        pos_neg_str = f"({b['positives']} pos / {b['negatives']} neg)"

        print(f"{target:<18} | {'ROC-AUC':<14} | {b['ROC_AUC']:<22.4f} | {e2['ROC_AUC']:<24.4f} | {d['ROC_AUC']:+<10.4f}")
        print(f"{pos_neg_str:<18} | {'PR-AUC':<14} | {b['PR_AUC']:<22.4f} | {e2['PR_AUC']:<24.4f} | {d['PR_AUC']:+<10.4f}")
        print(f"{'':<18} | {'Sensitivity':<14} | {b['Sensitivity']:<22.4f} | {e2['Sensitivity']:<24.4f} | {d['Sensitivity']:+<10.4f}")
        print(f"{'':<18} | {'Specificity':<14} | {b['Specificity']:<22.4f} | {e2['Specificity']:<24.4f} | {d['Specificity']:+<10.4f}")
        print(f"{'':<18} | {'Precision':<14} | {b['Precision']:<22.4f} | {e2['Precision']:<24.4f} | {d['Precision']:+<10.4f}")
        print(f"{'':<18} | {'F1 Score':<14} | {b['F1']:<22.4f} | {e2['F1']:<22.4f} | {d['F1']:+<10.4f}")
        print(f"{'':<18} | {'Threshold':<14} | {b['threshold']:<22.4f} | {e2['threshold']:<24.4f} | {'—':<10}")
        print(f"{'':<18} | {'TP / FP / FN / TN':<14} | {b['TP']}/{b['FP']}/{b['FN']}/{b['TN']:<20} | {e2['TP']}/{e2['FP']}/{e2['FN']}/{e2['TN']:<22} | {'—':<10}")
        print("-" * 110)

    print(f"{'MACRO AVERAGE':<18} | {'ROC-AUC':<14} | {macro_baseline['ROC_AUC']:<22.4f} | {macro_exp2['ROC_AUC']:<24.4f} | {macro_deltas['ROC_AUC']:+<10.4f}")
    print(f"{'':<18} | {'PR-AUC':<14} | {macro_baseline['PR_AUC']:<22.4f} | {macro_exp2['PR_AUC']:<22.4f} | {macro_deltas['PR_AUC']:+<10.4f}")
    print(f"{'':<18} | {'Sensitivity':<14} | {macro_baseline['Sensitivity']:<22.4f} | {macro_exp2['Sensitivity']:<22.4f} | {macro_deltas['Sensitivity']:+<10.4f}")
    print(f"{'':<18} | {'Specificity':<14} | {macro_baseline['Specificity']:<22.4f} | {macro_exp2['Specificity']:<22.4f} | {macro_deltas['Specificity']:+<10.4f}")
    print(f"{'':<18} | {'Precision':<14} | {macro_baseline['Precision']:<22.4f} | {macro_exp2['Precision']:<22.4f} | {macro_deltas['Precision']:+<10.4f}")
    print(f"{'':<18} | {'F1 Score':<14} | {macro_baseline['F1']:<22.4f} | {macro_exp2['F1']:<22.4f} | {macro_deltas['F1']:+<10.4f}")
    print("=" * 110)


if __name__ == "__main__":
    main()
