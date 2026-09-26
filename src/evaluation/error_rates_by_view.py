import json
import pandas as pd
import numpy as np


DIAGNOSTICS_PATH = (
    "outputs/evaluation/prediction_diagnostics.json"
)

VALIDATION_CSV = (
    "data/splits/validation_clean.csv"
)

TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]

THRESHOLDS = {
    "Atelectasis": {
        "Frontal": 0.34,
        "Lateral": 0.34
    },

    "Cardiomegaly": {
        "Frontal": 0.65,
        "Lateral": 0.22
    },

    "Consolidation": {
        "Frontal": 0.51,
        "Lateral": 0.46
    },

    "Edema": {
        "Frontal": 0.50,
        "Lateral": 0.16
    },

    "Pleural Effusion": {
        "Frontal": 0.52,
        "Lateral": 0.29
    }
}


print()
print("=" * 90)
print(
    "HC-XCDSS ERROR RATES BY VIEW"
)
print("=" * 90)


# ---------------------------------------------------------
# Load validation data
# ---------------------------------------------------------

df = pd.read_csv(
    VALIDATION_CSV
)

df["Path"] = df["Path"].astype(str)


# ---------------------------------------------------------
# Load reusable prediction table
# ---------------------------------------------------------

PREDICTION_TABLE_PATH = (
    "outputs/evaluation/image_level_predictions.csv"
)

predictions = pd.read_csv(
    PREDICTION_TABLE_PATH
)

predictions["Path"] = predictions["Path"].astype(str)


# ---------------------------------------------------------
# Analyze every target
# ---------------------------------------------------------

for target in TARGETS:

    probability_column = (
        f"{target}_probability"
    )

    true_column = (
        f"{target}_true"
    )

    print()
    print("-" * 90)
    print(target)
    print("-" * 90)


    for view in [
        "Frontal",
        "Lateral"
    ]:

        threshold = THRESHOLDS[target][view]


        # -------------------------------------------------
        # Select this view
        # -------------------------------------------------

        subset = predictions[
            predictions["View"] == view
        ].copy()


        # -------------------------------------------------
        # Only known labels
        # -------------------------------------------------

        subset = subset[
            subset[true_column].isin(
                [0.0, 1.0]
            )
        ]


        if len(subset) == 0:

            print()
            print(view)
            print("  No valid labels")
            continue


        y_true = subset[
            true_column
        ].to_numpy()


        y_probability = subset[
            probability_column
        ].to_numpy()


        # -------------------------------------------------
        # Apply view-specific threshold
        # -------------------------------------------------

        y_pred = (
            y_probability >= threshold
        ).astype(int)


        # -------------------------------------------------
        # Confusion matrix manually
        # -------------------------------------------------

        tn = np.sum(
            (y_true == 0) &
            (y_pred == 0)
        )

        fp = np.sum(
            (y_true == 0) &
            (y_pred == 1)
        )

        fn = np.sum(
            (y_true == 1) &
            (y_pred == 0)
        )

        tp = np.sum(
            (y_true == 1) &
            (y_pred == 1)
        )


        positive_count = (
            tp + fn
        )

        negative_count = (
            tn + fp
        )


        # -------------------------------------------------
        # Rates
        # -------------------------------------------------

        fn_rate = (
            fn / positive_count
            if positive_count > 0
            else 0
        )


        fp_rate = (
            fp / negative_count
            if negative_count > 0
            else 0
        )


        sensitivity = (
            tp / (tp + fn)
            if (tp + fn) > 0
            else 0
        )


        specificity = (
            tn / (tn + fp)
            if (tn + fp) > 0
            else 0
        )


        precision = (
            tp / (tp + fp)
            if (tp + fp) > 0
            else 0
        )


        f1 = (
            2 * precision * sensitivity /
            (precision + sensitivity)
            if (precision + sensitivity) > 0
            else 0
        )


        # -------------------------------------------------
        # Print
        # -------------------------------------------------

        print()
        print(view)

        print(
            f"  Threshold: "
            f"{threshold:.2f}"
        )

        print(
            f"  Available labels: "
            f"{len(subset)}"
        )

        print(
            f"  Positive cases: "
            f"{positive_count}"
        )

        print(
            f"  Negative cases: "
            f"{negative_count}"
        )

        print()

        print(
            f"  True positives: "
            f"{tp}"
        )

        print(
            f"  True negatives: "
            f"{tn}"
        )

        print(
            f"  False negatives: "
            f"{fn}"
        )

        print(
            f"  False positives: "
            f"{fp}"
        )

        print()

        print(
            f"  FN rate: "
            f"{fn_rate:.4f}"
        )

        print(
            f"  FP rate: "
            f"{fp_rate:.4f}"
        )

        print(
            f"  Sensitivity: "
            f"{sensitivity:.4f}"
        )

        print(
            f"  Specificity: "
            f"{specificity:.4f}"
        )

        print(
            f"  Precision: "
            f"{precision:.4f}"
        )

        print(
            f"  F1: "
            f"{f1:.4f}"
        )


print()
print("=" * 90)
print(
    "VIEW ERROR RATE ANALYSIS COMPLETED"
)
print("=" * 90)