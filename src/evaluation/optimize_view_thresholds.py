import json
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score


INPUT_PATH = (
    "outputs/evaluation/"
    "image_level_predictions.csv"
)

GLOBAL_THRESHOLD_PATH = (
    "models/checkpoints/"
    "optimal_thresholds_balanced.json"
)

OUTPUT_PATH = (
    "outputs/evaluation/"
    "view_specific_thresholds.json"
)


TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]


VIEWS = [
    "Frontal",
    "Lateral"
]


df = pd.read_csv(
    INPUT_PATH
)


with open(
    GLOBAL_THRESHOLD_PATH,
    "r"
) as file:

    global_thresholds = json.load(
        file
    )


print()
print("=" * 80)
print(
    "HC-XCDSS VIEW-SPECIFIC THRESHOLD OPTIMIZATION"
)
print("=" * 80)

print()
print(
    "Images:",
    len(df)
)


results = {}


thresholds_to_test = np.arange(
    0.05,
    0.96,
    0.01
)


for target in TARGETS:

    results[target] = {}

    print()
    print("-" * 80)
    print(target)
    print("-" * 80)

    probability_column = (
        f"{target}_probability"
    )

    true_column = (
        f"{target}_true"
    )


    global_threshold = (
        global_thresholds[target]
    )


    for view in VIEWS:

        view_df = df[
            df["View"] == view
        ].copy()


        valid = (
            view_df[true_column].isin(
                [0.0, 1.0]
            )
        )


        view_df = view_df[
            valid
        ]


        y_true = view_df[
            true_column
        ].astype(int).values


        y_scores = view_df[
            probability_column
        ].values


        print()
        print(
            view
        )

        print(
            "Available labels:",
            len(y_true)
        )


        if len(y_true) == 0:

            print(
                "No valid labels."
            )

            continue


        best_threshold = 0.5
        best_j = -1

        best_f1 = 0
        best_sensitivity = 0
        best_specificity = 0


        for threshold in thresholds_to_test:

            y_pred = (
                y_scores >= threshold
            ).astype(int)


            tn, fp, fn, tp = (
                confusion_matrix(
                    y_true,
                    y_pred,
                    labels=[0, 1]
                ).ravel()
            )


            sensitivity = (
                tp / (tp + fn)
                if tp + fn > 0
                else 0
            )


            specificity = (
                tn / (tn + fp)
                if tn + fp > 0
                else 0
            )


            j_score = (
                sensitivity
                + specificity
                - 1
            )


            f1 = f1_score(
                y_true,
                y_pred,
                zero_division=0
            )


            if j_score > best_j:

                best_j = j_score

                best_threshold = (
                    threshold
                )

                best_f1 = f1

                best_sensitivity = (
                    sensitivity
                )

                best_specificity = (
                    specificity
                )


        global_pred = (
            y_scores >= global_threshold
        ).astype(int)


        gtn, gfp, gfn, gtp = (
            confusion_matrix(
                y_true,
                global_pred,
                labels=[0, 1]
            ).ravel()
        )


        global_sensitivity = (
            gtp / (gtp + gfn)
            if gtp + gfn > 0
            else 0
        )


        global_specificity = (
            gtn / (gtn + gfp)
            if gtn + gfp > 0
            else 0
        )


        global_f1 = f1_score(
            y_true,
            global_pred,
            zero_division=0
        )


        results[target][view] = {

            "global_threshold":
                float(global_threshold),

            "optimal_threshold":
                float(best_threshold),

            "youden_j":
                float(best_j),

            "optimal_f1":
                float(best_f1),

            "optimal_sensitivity":
                float(best_sensitivity),

            "optimal_specificity":
                float(best_specificity),

            "global_f1":
                float(global_f1),

            "global_sensitivity":
                float(global_sensitivity),

            "global_specificity":
                float(global_specificity),

            "samples":
                int(len(y_true))
        }


        print(
            f"Global threshold: "
            f"{global_threshold:.2f}"
        )

        print(
            f"Optimal threshold: "
            f"{best_threshold:.2f}"
        )

        print(
            f"Global F1: "
            f"{global_f1:.4f}"
        )

        print(
            f"Optimal F1: "
            f"{best_f1:.4f}"
        )

        print(
            f"Global Sensitivity: "
            f"{global_sensitivity:.4f}"
        )

        print(
            f"Optimal Sensitivity: "
            f"{best_sensitivity:.4f}"
        )

        print(
            f"Global Specificity: "
            f"{global_specificity:.4f}"
        )

        print(
            f"Optimal Specificity: "
            f"{best_specificity:.4f}"
        )


with open(
    OUTPUT_PATH,
    "w"
) as file:

    json.dump(
        results,
        file,
        indent=4
    )


print()
print("=" * 80)
print(
    "VIEW-SPECIFIC THRESHOLD RESULTS"
)
print("=" * 80)


for target in TARGETS:

    print()
    print(target)

    for view in VIEWS:

        if view not in results[target]:
            continue

        values = results[
            target
        ][view]

        print(
            f"  {view}: "
            f"{values['optimal_threshold']:.2f}"
        )


print()
print(
    "Saved:"
)

print(
    OUTPUT_PATH
)

print()
print("=" * 80)
print(
    "VIEW-SPECIFIC THRESHOLD OPTIMIZATION COMPLETED"
)
print("=" * 80)