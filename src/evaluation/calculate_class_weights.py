import pandas as pd


TRAIN_CSV = "data/splits/train_clean.csv"


TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]


df = pd.read_csv(
    TRAIN_CSV
)


print()
print("=" * 70)
print("CLASS BALANCE")
print("=" * 70)


for target in TARGETS:

    valid = df[target].notna()

    y = df.loc[
        valid,
        target
    ]

    positive = (
        y == 1
    ).sum()

    negative = (
        y == 0
    ).sum()

    total = positive + negative


    positive_ratio = (
        positive / total
    )

    negative_ratio = (
        negative / total
    )


    positive_weight = (
        total / (2 * positive)
    )

    negative_weight = (
        total / (2 * negative)
    )


    print()
    print(target)

    print(
        "Positive:",
        positive
    )

    print(
        "Negative:",
        negative
    )

    print(
        "Positive ratio:",
        f"{positive_ratio:.4f}"
    )

    print(
        "Negative ratio:",
        f"{negative_ratio:.4f}"
    )

    print(
        "Positive weight:",
        f"{positive_weight:.4f}"
    )

    print(
        "Negative weight:",
        f"{negative_weight:.4f}"
    )


print()
print("=" * 70)