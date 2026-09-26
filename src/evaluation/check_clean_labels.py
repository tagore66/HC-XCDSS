import pandas as pd

TRAIN_CSV = "data/splits/train_clean.csv"
VALIDATION_CSV = "data/splits/validation_clean.csv"

TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]


def analyze_file(path):

    print()
    print("=" * 70)
    print(path)
    print("=" * 70)

    df = pd.read_csv(path)

    print()
    print("Dataset shape:")
    print(df.shape)

    print()

    for target in TARGETS:

        print("-" * 70)
        print(target)

        print(
            df[target].value_counts(
                dropna=False
            )
        )

        print()

        available = df[target].notna().sum()

        positive = (
            df[target] == 1
        ).sum()

        negative = (
            df[target] == 0
        ).sum()

        uncertain = (
            df[target] == -1
        ).sum()

        print(
            "Available:",
            available
        )

        print(
            "Positive:",
            positive
        )

        print(
            "Negative:",
            negative
        )

        print(
            "Uncertain:",
            uncertain
        )


analyze_file(TRAIN_CSV)

analyze_file(VALIDATION_CSV)