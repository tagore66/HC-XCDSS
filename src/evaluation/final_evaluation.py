import json
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
)


# ============================================================
# HC-XCDSS FINAL EVALUATION
# ============================================================

STUDY_PREDICTIONS = (
    "outputs/evaluation/study_level_predictions.csv"
)

IMAGE_PREDICTIONS = (
    "outputs/evaluation/image_level_predictions.csv"
)

OUTPUT_DIR = Path(
    "outputs/evaluation/final"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion",
]


# ============================================================
# LOAD DATA
# ============================================================

print()
print("=" * 80)
print("HC-XCDSS FINAL EVALUATION")
print("=" * 80)


print()
print("Loading study-level predictions...")


study_df = pd.read_csv(
    STUDY_PREDICTIONS
)


print(
    "Study rows:",
    len(study_df)
)


print()
print("Loading image-level predictions...")


image_df = pd.read_csv(
    IMAGE_PREDICTIONS
)


print(
    "Image rows:",
    len(image_df)
)


# ============================================================
# HELPER
# ============================================================

def calculate_metrics(
    y_true,
    y_score,
    threshold
):

    y_pred = (
        y_score >= threshold
    ).astype(int)


    auc = roc_auc_score(
        y_true,
        y_score
    )


    pr_auc = average_precision_score(
        y_true,
        y_score
    )


    precision = precision_score(
        y_true,
        y_pred,
        zero_division=0
    )


    sensitivity = recall_score(
        y_true,
        y_pred,
        zero_division=0
    )


    f1 = f1_score(
        y_true,
        y_pred,
        zero_division=0
    )


    tn, fp, fn, tp = (
        confusion_matrix(
            y_true,
            y_pred,
            labels=[0, 1]
        ).ravel()
    )


    specificity = (
        tn / (tn + fp)
        if (tn + fp) > 0
        else 0.0
    )


    return {
        "samples": int(len(y_true)),
        "threshold": float(threshold),
        "ROC_AUC": float(auc),
        "PR_AUC": float(pr_auc),
        "Precision": float(precision),
        "Sensitivity": float(sensitivity),
        "Specificity": float(specificity),
        "F1": float(f1),
        "TN": int(tn),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
    }


# ============================================================
# STUDY-LEVEL EVALUATION
# ============================================================

print()
print("=" * 80)
print("STUDY-LEVEL FINAL METRICS")
print("=" * 80)


study_results = []


for target in TARGETS:

    label_column = (
        f"{target}_label"
    )

    score_column = (
        f"{target}_score"
    )

    threshold_column = (
        f"{target}_threshold"
    )


    labels = study_df[
        label_column
    ].values


    scores = study_df[
        score_column
    ].values


    thresholds = study_df[
        threshold_column
    ].dropna()


    if len(thresholds) == 0:

        print(
            f"\n{target}: "
            "No threshold available."
        )

        continue


    threshold = float(
        thresholds.iloc[0]
    )


    valid = (
        ~np.isnan(labels)
        &
        ~np.isnan(scores)
    )


    y_true = labels[
        valid
    ].astype(int)


    y_score = scores[
        valid
    ]


    if len(
        np.unique(y_true)
    ) < 2:

        print(
            f"\n{target}: "
            "Insufficient class variation."
        )

        continue


    metrics = calculate_metrics(
        y_true,
        y_score,
        threshold
    )


    metrics["Finding"] = target


    metrics["Level"] = (
        "Study"
    )


    study_results.append(
        metrics
    )


    print()
    print(
        target
    )

    print(
        "-" * 60
    )

    print(
        f"Samples:      {metrics['samples']}"
    )

    print(
        f"Threshold:    {metrics['threshold']:.2f}"
    )

    print(
        f"ROC-AUC:      {metrics['ROC_AUC']:.4f}"
    )

    print(
        f"PR-AUC:       {metrics['PR_AUC']:.4f}"
    )

    print(
        f"Precision:    {metrics['Precision']:.4f}"
    )

    print(
        f"Sensitivity:  {metrics['Sensitivity']:.4f}"
    )

    print(
        f"Specificity:  {metrics['Specificity']:.4f}"
    )

    print(
        f"F1:           {metrics['F1']:.4f}"
    )

    print(
        f"TN: {metrics['TN']}  "
        f"FP: {metrics['FP']}  "
        f"FN: {metrics['FN']}  "
        f"TP: {metrics['TP']}"
    )


# ============================================================
# SAVE STUDY METRICS
# ============================================================

study_metrics_df = pd.DataFrame(
    study_results
)


study_metrics_path = (
    OUTPUT_DIR /
    "study_level_metrics.csv"
)


study_metrics_df.to_csv(
    study_metrics_path,
    index=False
)


# ============================================================
# IMAGE-LEVEL EVALUATION
# ============================================================

print()
print("=" * 80)
print("IMAGE-LEVEL FINAL METRICS")
print("=" * 80)


image_results = []


for target in TARGETS:

    label_column = (
        f"{target}_true"
    )

    score_column = (
        f"{target}_probability"
    )


    labels = image_df[
        label_column
    ].values


    scores = image_df[
        score_column
    ].values


    # --------------------------------------------------------
    # Use the final production threshold.
    # --------------------------------------------------------

    threshold_map = {

        "Atelectasis": 0.34,

        "Cardiomegaly": 0.59,

        "Consolidation": 0.49,

        "Edema": 0.50,

        "Pleural Effusion": 0.50,

    }


    threshold = threshold_map[
        target
    ]


    valid = (
        ~pd.isna(labels)
        &
        ~pd.isna(scores)
    )


    y_true = labels[
        valid
    ].astype(int)


    y_score = scores[
        valid
    ]


    if len(
        np.unique(y_true)
    ) < 2:

        continue


    metrics = calculate_metrics(
        y_true,
        y_score,
        threshold
    )


    metrics["Finding"] = target


    metrics["Level"] = (
        "Image"
    )


    image_results.append(
        metrics
    )


    print()
    print(
        target
    )

    print(
        "-" * 60
    )

    print(
        f"Samples:      {metrics['samples']}"
    )

    print(
        f"Threshold:    {metrics['threshold']:.2f}"
    )

    print(
        f"ROC-AUC:      {metrics['ROC_AUC']:.4f}"
    )

    print(
        f"PR-AUC:       {metrics['PR_AUC']:.4f}"
    )

    print(
        f"Precision:    {metrics['Precision']:.4f}"
    )

    print(
        f"Sensitivity:  {metrics['Sensitivity']:.4f}"
    )

    print(
        f"Specificity:  {metrics['Specificity']:.4f}"
    )

    print(
        f"F1:           {metrics['F1']:.4f}"
    )


# ============================================================
# SAVE IMAGE METRICS
# ============================================================

image_metrics_df = pd.DataFrame(
    image_results
)


image_metrics_path = (
    OUTPUT_DIR /
    "image_level_metrics.csv"
)


image_metrics_df.to_csv(
    image_metrics_path,
    index=False
)


# ============================================================
# COMBINED METRICS
# ============================================================

combined_df = pd.concat(
    [
        study_metrics_df,
        image_metrics_df
    ],
    ignore_index=True
)


combined_path = (
    OUTPUT_DIR /
    "final_metrics.csv"
)


combined_df.to_csv(
    combined_path,
    index=False
)


# ============================================================
# JSON REPORT
# ============================================================

report = {

    "project":
        "HC-XCDSS",

    "model":
        "DenseNet-121",

    "findings":
        TARGETS,

    "study_level":
        study_results,

    "image_level":
        image_results,

}


json_path = (
    OUTPUT_DIR /
    "final_evaluation_report.json"
)


with open(
    json_path,
    "w"
) as file:

    json.dump(
        report,
        file,
        indent=2
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 80)
print("FINAL EVALUATION SUMMARY")
print("=" * 80)


for result in study_results:

    print(
        f"{result['Finding']:<20} "
        f"AUC={result['ROC_AUC']:.4f}  "
        f"F1={result['F1']:.4f}  "
        f"Sens={result['Sensitivity']:.4f}  "
        f"Spec={result['Specificity']:.4f}"
    )


print()
print("=" * 80)
print("FILES SAVED")
print("=" * 80)


print(
    study_metrics_path
)

print(
    image_metrics_path
)

print(
    combined_path
)

print(
    json_path
)


print()
print("=" * 80)
print("FINAL EVALUATION COMPLETED")
print("=" * 80)