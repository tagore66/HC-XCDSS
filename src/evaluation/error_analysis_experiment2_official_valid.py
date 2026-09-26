import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from PIL import Image
from torchvision import transforms

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

JSON_OUT = OUTPUT_DIR / "official_valid_error_analysis_experiment2.json"
CSV_OUT = OUTPUT_DIR / "official_valid_error_analysis_experiment2.csv"

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
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

TRANSFORM_320 = transforms.Compose([
    transforms.Resize((320, 320)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])


def load_model(checkpoint_path):
    model = CheXpertDenseNet(num_classes=5).to(DEVICE)
    ckpt = torch.load(checkpoint_path, map_location=DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model


def run_inference(model, transform, df):
    probs = []
    for _, row in df.iterrows():
        rel_path = str(row["Path"]).replace("CheXpert-v1.0-small/", "")
        img_path = DATA_DIR / rel_path
        img = Image.open(img_path).convert("RGB")
        tensor = transform(img).unsqueeze(0).to(DEVICE)
        with torch.inference_mode():
            out = model(tensor)
            p = torch.sigmoid(out)[0].cpu().numpy()
        probs.append(p)
    return np.array(probs)


def main():
    df = pd.read_csv(VALID_CSV)
    print(f"Loaded {len(df)} cases from {VALID_CSV.name}")

    print("Running Baseline Model inference (224x224)...")
    base_model = load_model(BASELINE_CKPT)
    b_probs = run_inference(base_model, TRANSFORM_224, df)
    del base_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    print("Running Experiment 2 Model inference (320x320, NoAug)...")
    exp2_model = load_model(EXP2_CKPT)
    e2_probs = run_inference(exp2_model, TRANSFORM_320, df)
    del exp2_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    full_records = []
    summary_by_finding = {}

    for t_idx, target in enumerate(TARGETS):
        b_thresh = BASELINE_THRESHOLDS[target]
        e2_thresh = EXP2_THRESHOLDS[target]
        y_true = df[target].to_numpy(dtype=int)

        b_p = b_probs[:, t_idx]
        e2_p = e2_probs[:, t_idx]
        b_pred = (b_p >= b_thresh).astype(int)
        e2_pred = (e2_p >= e2_thresh).astype(int)

        b_correct = (b_pred == y_true)
        e2_correct = (e2_pred == y_true)

        correct_to_incorrect = []  # Baseline Correct -> Exp2 Incorrect
        incorrect_to_correct = []  # Baseline Incorrect -> Exp2 Correct
        both_correct = []
        both_incorrect = []

        pos_mask = (y_true == 1)
        neg_mask = (y_true == 0)

        pos_prob_increased = int(np.sum((e2_p > b_p) & pos_mask))
        pos_prob_decreased = int(np.sum((e2_p < b_p) & pos_mask))
        pos_prob_unchanged = int(np.sum((e2_p == b_p) & pos_mask))

        neg_prob_decreased = int(np.sum((e2_p < b_p) & neg_mask))  # improved towards 0
        neg_prob_increased = int(np.sum((e2_p > b_p) & neg_mask))  # regressed towards 1
        neg_prob_unchanged = int(np.sum((e2_p == b_p) & neg_mask))

        # Categorical movements
        pos_fn_to_tp = int(np.sum((b_pred == 0) & (e2_pred == 1) & pos_mask))  # FN -> TP (gain)
        pos_tp_to_fn = int(np.sum((b_pred == 1) & (e2_pred == 0) & pos_mask))  # TP -> FN (loss)

        neg_fp_to_tn = int(np.sum((b_pred == 1) & (e2_pred == 0) & neg_mask))  # FP -> TN (gain)
        neg_tn_to_fp = int(np.sum((b_pred == 0) & (e2_pred == 1) & neg_mask))  # TN -> FP (loss)

        prob_shifts = []

        for i in range(len(df)):
            p_path = df["Path"].iloc[i]
            gt = int(y_true[i])
            bp = float(b_p[i])
            ep = float(e2_p[i])
            shift = float(ep - bp)
            abs_shift = abs(shift)

            bc = bool(b_correct[i])
            ec = bool(e2_correct[i])

            transition_type = "NO_CHANGE"
            if bc and not ec:
                transition_type = "BASELINE_CORRECT_TO_EXP2_INCORRECT"
                correct_to_incorrect.append({
                    "path": p_path,
                    "ground_truth": gt,
                    "baseline_prob": round(bp, 6),
                    "exp2_prob": round(ep, 6),
                    "prob_shift": round(shift, 6),
                    "baseline_pred": int(b_pred[i]),
                    "exp2_pred": int(e2_pred[i]),
                    "baseline_threshold": b_thresh,
                    "exp2_threshold": e2_thresh
                })
            elif not bc and ec:
                transition_type = "BASELINE_INCORRECT_TO_EXP2_CORRECT"
                incorrect_to_correct.append({
                    "path": p_path,
                    "ground_truth": gt,
                    "baseline_prob": round(bp, 6),
                    "exp2_prob": round(ep, 6),
                    "prob_shift": round(shift, 6),
                    "baseline_pred": int(b_pred[i]),
                    "exp2_pred": int(e2_pred[i]),
                    "baseline_threshold": b_thresh,
                    "exp2_threshold": e2_thresh
                })
            elif bc and ec:
                both_correct.append(p_path)
            else:
                both_incorrect.append(p_path)

            record = {
                "path": p_path,
                "finding": target,
                "ground_truth": gt,
                "baseline_threshold": b_thresh,
                "exp2_threshold": e2_thresh,
                "baseline_probability": round(bp, 6),
                "experiment2_probability": round(ep, 6),
                "probability_shift": round(shift, 6),
                "absolute_shift": round(abs_shift, 6),
                "baseline_prediction": int(b_pred[i]),
                "experiment2_prediction": int(e2_pred[i]),
                "baseline_correct": bc,
                "experiment2_correct": ec,
                "transition_type": transition_type
            }
            full_records.append(record)
            prob_shifts.append(record)

        largest_shifts = sorted(prob_shifts, key=lambda x: x["absolute_shift"], reverse=True)[:5]

        summary_by_finding[target] = {
            "total_cases": len(df),
            "positives": int(np.sum(pos_mask)),
            "negatives": int(np.sum(neg_mask)),
            "baseline_threshold": b_thresh,
            "exp2_threshold": e2_thresh,
            "positive_cases": {
                "FN_to_TP_gain": pos_fn_to_tp,
                "TP_to_FN_loss": pos_tp_to_fn,
                "prob_increased_towards_1": pos_prob_increased,
                "prob_decreased_away_from_1": pos_prob_decreased,
                "prob_unchanged": pos_prob_unchanged
            },
            "negative_cases": {
                "FP_to_TN_gain": neg_fp_to_tn,
                "TN_to_FP_loss": neg_tn_to_fp,
                "prob_decreased_towards_0": neg_prob_decreased,
                "prob_increased_away_from_0": neg_prob_increased,
                "prob_unchanged": neg_prob_unchanged
            },
            "transitions": {
                "baseline_correct_to_exp2_incorrect_count": len(correct_to_incorrect),
                "baseline_incorrect_to_exp2_correct_count": len(incorrect_to_correct),
                "both_correct_count": len(both_correct),
                "both_incorrect_count": len(both_incorrect),
                "baseline_correct_to_exp2_incorrect_cases": correct_to_incorrect,
                "baseline_incorrect_to_exp2_correct_cases": incorrect_to_correct
            },
            "largest_probability_shifts": largest_shifts
        }

    # Save CSV
    records_df = pd.DataFrame(full_records)
    records_df.to_csv(CSV_OUT, index=False)
    print(f"Saved error analysis CSV: {CSV_OUT}")

    # Save JSON
    full_json = {
        "cohort": "Official CheXpert Radiologist Consensus Validation Set (234 cases)",
        "model_comparison": "Baseline (224x224) vs Experiment 2 (320x320, NoAug)",
        "summary_by_finding": summary_by_finding
    }
    with open(JSON_OUT, "w") as f:
        json.dump(full_json, f, indent=4)
    print(f"Saved error analysis JSON: {JSON_OUT}")

    # Terminal Output
    print("\n" + "=" * 105)
    print("OFFICIAL VALIDATION DETAILED ERROR ANALYSIS: BASELINE vs. EXPERIMENT 2")
    print("=" * 105)
    for target in TARGETS:
        s = summary_by_finding[target]
        print(f"\n>>> {target.upper()} (GT: {s['positives']} Pos / {s['negatives']} Neg | Thresh: Base={s['baseline_threshold']}, Exp2={s['exp2_threshold']})")
        print(f"  Positive Cases (GT=1): {s['positive_cases']['FN_to_TP_gain']} FN->TP (gain) | {s['positive_cases']['TP_to_FN_loss']} TP->FN (loss) | {s['positive_cases']['prob_increased_towards_1']} prob up / {s['positive_cases']['prob_decreased_away_from_1']} prob down")
        print(f"  Negative Cases (GT=0): {s['negative_cases']['FP_to_TN_gain']} FP->TN (gain) | {s['negative_cases']['TN_to_FP_loss']} TN->FP (loss) | {s['negative_cases']['prob_decreased_towards_0']} prob down / {s['negative_cases']['prob_increased_away_from_0']} prob up")
        print(f"  Transitions: Base Correct -> Exp2 Incorrect: {s['transitions']['baseline_correct_to_exp2_incorrect_count']} | Base Incorrect -> Exp2 Correct: {s['transitions']['baseline_incorrect_to_exp2_correct_count']}")
        if s['transitions']['baseline_correct_to_exp2_incorrect_count'] > 0:
            print("    [Base Correct -> Exp2 Incorrect Details]:")
            for c in s['transitions']['baseline_correct_to_exp2_incorrect_cases'][:5]:
                print(f"      - {Path(c['path']).name} (GT={c['ground_truth']}): Base={c['baseline_prob']:.4f} (pred {c['baseline_pred']}) -> Exp2={c['exp2_prob']:.4f} (pred {c['exp2_pred']}) [Shift: {c['prob_shift']:+.4f}]")
        if s['transitions']['baseline_incorrect_to_exp2_correct_count'] > 0:
            print("    [Base Incorrect -> Exp2 Correct Details]:")
            for c in s['transitions']['baseline_incorrect_to_exp2_correct_cases'][:5]:
                print(f"      - {Path(c['path']).name} (GT={c['ground_truth']}): Base={c['baseline_prob']:.4f} (pred {c['baseline_pred']}) -> Exp2={c['exp2_prob']:.4f} (pred {c['exp2_pred']}) [Shift: {c['prob_shift']:+.4f}]")


if __name__ == "__main__":
    main()
