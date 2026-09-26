import json
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix
)


TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]


THRESHOLD_PATH = (
    Path("models")
    / "checkpoints"
    / "optimal_thresholds_balanced.json"
)


def load_thresholds():

    with open(
        THRESHOLD_PATH,
        "r"
    ) as file:

        return json.load(file)


def calculate_metrics(
    predictions,
    targets,
    masks
):

    results = {}

    predictions = np.asarray(
        predictions
    )

    targets = np.asarray(
        targets
    )

    masks = np.asarray(
        masks
    )

    thresholds = load_thresholds()


    for index, target in enumerate(
        TARGETS
    ):

        valid = masks[:, index]

        y_true = targets[
            valid,
            index
        ]

        y_score = predictions[
            valid,
            index
        ]


        if len(y_true) == 0:

            continue


        y_true = np.where(
            y_true == -1,
            0,
            y_true
        )


        if len(
            np.unique(y_true)
        ) < 2:

            continue


        threshold = float(
            thresholds[target]
        )


        y_pred = (
            y_score >= threshold
        ).astype(int)


        roc_auc = roc_auc_score(
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


        tn, fp, fn, tp = confusion_matrix(
            y_true,
            y_pred,
            labels=[0, 1]
        ).ravel()


        specificity = (
            tn / (tn + fp)
            if (tn + fp) > 0
            else 0
        )


        results[target] = {

            "Threshold":
                threshold,

            "ROC_AUC":
                float(roc_auc),

            "PR_AUC":
                float(pr_auc),

            "Precision":
                float(precision),

            "Sensitivity":
                float(sensitivity),

            "Specificity":
                float(specificity),

            "F1":
                float(f1),

            "TN":
                int(tn),

            "FP":
                int(fp),

            "FN":
                int(fn),

            "TP":
                int(tp)
        }


    return results