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
EXP1_CKPT = PROJECT_ROOT / "models" / "checkpoints" / "densenet121_320_aug_best.pth"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "evaluation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JSON_OUT = OUTPUT_DIR / "official_valid_error_analysis.json"
CSV_OUT = OUTPUT_DIR / "official_valid_error_analysis.csv"

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

EXP1_THRESHOLDS = {
    "Atelectasis": 0.3702,
    "Cardiomegaly": 0.5434,
    "Consolidation": 0.4253,
    "Edema": 0.5356,
    "Pleural Effusion": 0.4968
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

    print("Running Experiment 1 Model inference (320x320)...")
    exp1_model = load_model(EXP1_CKPT)
    e_probs = run_inference(exp1_model, TRANSFORM_320, df)
    del exp1_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    full_records = []
    summary_by_finding = {}

    for t_idx, target in enumerate(TARGETS):
        b_thresh = BASELINE_THRESHOLDS[target]
        e_thresh = EXP1_THRESHOLDS[target]
        y_true = df[target].to_numpy(dtype=int)

        b_p = b_probs[:, t_idx]
        e_p = e_probs[:, t_idx]
        b_pred = (b_p >= b_thresh).astype(int)
        e_pred = (e_p >= e_thresh).astype(int)

        b_correct = (b_pred == y_true)
        e_correct = (e_pred == y_true)

        # Categorical transitions
        correct_to_incorrect = []  # Baseline Correct -> Exp1 Incorrect
        incorrect_to_correct = []  # Baseline Incorrect -> Exp1 Correct
        both_correct = []
        both_incorrect = []

        # Probability shift directions
        # For positives (y=1): prob increase means improved calibration/confidence towards 1
        pos_mask = (y_true == 1)
        neg_mask = (y_true == 0)

        pos_prob_increased = int(np.sum((e_p > b_p) & pos_mask))
        pos_prob_decreased = int(np.sum((e_p < b_p) & pos_mask))
        pos_prob_unchanged = int(np.sum((e_p == b_p) & pos_mask))

        neg_prob_decreased = int(np.sum((e_p < b_p) & neg_mask))  # improved towards 0
        neg_prob_increased = int(np.sum((e_p > b_p) & neg_mask))  # regressed towards 1
        neg_prob_unchanged = int(np.sum((e_p == b_p) & neg_mask))

        # Categorical improvements / regressions
        # Positives: FN -> TP (improved), TP -> FN (regressed)
        pos_cat_improved = int(np.sum((b_pred == 0) & (e_pred == 1) & pos_mask))
        pos_cat_regressed = int(np.sum((b_pred == 1) & (e_pred == 0) & pos_mask))

        # Negatives: FP -> TN (improved), TN -> FP (regressed)
        neg_cat_improved = int(np.sum((b_pred == 1) & (e_pred == 0) & neg_mask))
        neg_cat_regressed = int(np.sum((b_pred == 0) & (e_pred == 1) & neg_mask))

        prob_shifts = []

        for i in range(len(df)):
            p_path = df["Path"].iloc[i]
            img_id = Path(p_path).stem + "_" + Path(p_path).parent.parent.name
            gt = int(y_true[i])
            bp = float(b_p[i])
            ep = float(e_p[i])
            shift = float(ep - bp)
            abs_shift = abs(shift)

            bc = bool(b_correct[i])
            ec = bool(e_correct[i])

            transition_type = "NO_CHANGE"
            if bc and not ec:
                transition_type = "BASELINE_CORRECT_TO_EXP1_INCORRECT"
                correct_to_incorrect.append({
                    "path": p_path,
                    "ground_truth": gt,
                    "baseline_prob": round(bp, 6),
                    "exp1_prob": round(ep, 6),
                    "prob_shift": round(shift, 6),
                    "baseline_pred": int(b_pred[i]),
                    "exp1_pred": int(e_pred[i]),
                    "baseline_threshold": b_thresh,
                    "exp1_threshold": e_thresh
                })
            elif not bc and ec:
                transition_type = "BASELINE_INCORRECT_TO_EXP1_CORRECT"
                incorrect_to_correct.append({
                    "path": p_path,
                    "ground_truth": gt,
                    "baseline_prob": round(bp, 6),
                    "exp1_prob": round(ep, 6),
                    "prob_shift": round(shift, 6),
                    "baseline_pred": int(b_pred[i]),
                    "exp1_pred": int(e_pred[i]),
                    "baseline_threshold": b_thresh,
                    "exp1_threshold": e_thresh
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
                "exp1_threshold": e_thresh,
                "baseline_probability": round(bp, 6),
                "exp1_probability": round(ep, 6),
                "probability_shift": round(shift, 6),
                "absolute_shift": round(abs_shift, 6),
                "baseline_prediction": int(b_pred[i]),
                "exp1_prediction": int(e_pred[i]),
                "baseline_correct": bc,
                "exp1_correct": ec,
                "transition_type": transition_type
            }
            full_records.append(record)
            prob_shifts.append(record)

        # Sort largest absolute probability shifts
        largest_shifts = sorted(prob_shifts, key=lambda x: x["absolute_shift"], reverse=True)[:5]

        summary_by_finding[target] = {
            "total_cases": len(df),
            "positives": int(np.sum(pos_mask)),
            "negatives": int(np.sum(neg_mask)),
            "baseline_threshold": b_thresh,
            "exp1_threshold": e_thresh,
            "positive_cases": {
                "categorical_improved_FN_to_TP": pos_cat_improved,
                "categorical_regressed_TP_to_FN": pos_cat_regressed,
                "prob_increased_towards_1": pos_prob_increased,
                "prob_decreased_away_from_1": pos_prob_decreased,
                "prob_unchanged": pos_prob_unchanged
            },
            "negative_cases": {
                "categorical_improved_FP_to_TN": neg_cat_improved,
                "categorical_regressed_TN_to_FP": neg_cat_regressed,
                "prob_decreased_towards_0": neg_prob_decreased,
                "prob_increased_away_from_0": neg_prob_increased,
                "prob_unchanged": neg_prob_unchanged
            },
            "transitions": {
                "baseline_correct_to_exp1_incorrect_count": len(correct_to_incorrect),
                "baseline_incorrect_to_exp1_correct_count": len(incorrect_to_correct),
                "both_correct_count": len(both_correct),
                "both_incorrect_count": len(both_incorrect),
                "baseline_correct_to_exp1_incorrect_cases": correct_to_incorrect,
                "baseline_incorrect_to_exp1_correct_cases": incorrect_to_correct
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
        "summary_by_finding": summary_by_finding
    }
    with open(JSON_OUT, "w") as f:
        json.dump(full_json, f, indent=4)
    print(f"Saved error analysis JSON: {JSON_OUT}")

    print("\n" + "=" * 105)
    print("OFFICIAL VALIDATION DETAILED ERROR ANALYSIS")
    print("=" * 105)
    for target in TARGETS:
        s = summary_by_finding[target]
        print(f"\n>>> {target.upper()} (GT: {s['positives']} Pos / {s['negatives']} Neg | Thresh: Base={s['baseline_threshold']}, Exp1={s['exp1_threshold']})")
        print(f"  Positive Cases (GT=1): {s['positive_cases']['categorical_improved_FN_to_TP']} FN->TP (gain) | {s['positive_cases']['categorical_regressed_TP_to_FN']} TP->FN (loss) | {s['positive_cases']['prob_increased_towards_1']} prob up / {s['positive_cases']['prob_decreased_away_from_1']} prob down")
        print(f"  Negative Cases (GT=0): {s['negative_cases']['categorical_improved_FP_to_TN']} FP->TN (gain) | {s['negative_cases']['categorical_regressed_TN_to_FP']} TN->FP (loss) | {s['negative_cases']['prob_decreased_towards_0']} prob down / {s['negative_cases']['prob_increased_away_from_0']} prob up")
        print(f"  Classification Transitions: Base Correct -> Exp1 Incorrect: {s['transitions']['baseline_correct_to_exp1_incorrect_count']} | Base Incorrect -> Exp1 Correct: {s['transitions']['baseline_incorrect_to_exp1_correct_count']}")
        if s['transitions']['baseline_correct_to_exp1_incorrect_count'] > 0:
            print("    [Base Correct -> Exp1 Incorrect Details]:")
            for c in s['transitions']['baseline_correct_to_exp1_incorrect_cases'][:5]:
                print(f"      - {Path(c['path']).name} (GT={c['ground_truth']}): Base={c['baseline_prob']:.4f} (pred {c['baseline_pred']}) -> Exp1={c['exp1_prob']:.4f} (pred {c['exp1_pred']}) [Shift: {c['prob_shift']:+.4f}]")
        if s['transitions']['baseline_incorrect_to_exp1_correct_count'] > 0:
            print("    [Base Incorrect -> Exp1 Correct Details]:")
            for c in s['transitions']['baseline_incorrect_to_exp1_correct_cases'][:5]:
                print(f"      - {Path(c['path']).name} (GT={c['ground_truth']}): Base={c['baseline_prob']:.4f} (pred {c['baseline_pred']}) -> Exp1={c['exp1_prob']:.4f} (pred {c['exp1_pred']}) [Shift: {c['prob_shift']:+.4f}]")


if __name__ == "__main__":
    main()
