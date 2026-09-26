import json
import pandas as pd

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


diagnostics = json.load(
    open(DIAGNOSTICS_PATH, "r")
)

df = pd.read_csv(
    VALIDATION_CSV
)

df["Path"] = df["Path"].astype(str)


def normalize_view(value):

    if pd.isna(value):
        return "Unknown"

    return str(value)


def get_view(path):

    row = df[
        df["Path"] == path
    ]

    if len(row) == 0:
        return "Unknown"

    return normalize_view(
        row.iloc[0]["Frontal/Lateral"]
    )


print()
print("=" * 80)
print("HC-XCDSS ERROR ANALYSIS BY VIEW")
print("=" * 80)


for target in TARGETS:

    finding = diagnostics[
        "findings"
    ][target]

    false_positives = (
        finding["false_positives"]
    )

    false_negatives = (
        finding["false_negatives"]
    )


    fp_counts = {}

    fn_counts = {}


    for record in false_positives:

        view = get_view(
            record["image"]
        )

        fp_counts[view] = (
            fp_counts.get(view, 0) + 1
        )


    for record in false_negatives:

        view = get_view(
            record["image"]
        )

        fn_counts[view] = (
            fn_counts.get(view, 0) + 1
        )


    print()
    print("-" * 80)
    print(target)
    print("-" * 80)


    print()
    print("FALSE POSITIVES")

    for view in [
        "Frontal",
        "Lateral",
        "Unknown"
    ]:

        print(
            f"  {view}: "
            f"{fp_counts.get(view, 0)}"
        )


    print()
    print("FALSE NEGATIVES")

    for view in [
        "Frontal",
        "Lateral",
        "Unknown"
    ]:

        print(
            f"  {view}: "
            f"{fn_counts.get(view, 0)}"
        )


print()
print("=" * 80)
print("VIEW DISTRIBUTION")
print("=" * 80)

print(
    df["Frontal/Lateral"]
    .value_counts(dropna=False)
)


print()
print("=" * 80)
print("ERROR ANALYSIS COMPLETED")
print("=" * 80)