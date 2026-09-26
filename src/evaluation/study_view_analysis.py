import pandas as pd


TRAIN_CSV = (
    "data/splits/train_clean.csv"
)

VALIDATION_CSV = (
    "data/splits/validation_clean.csv"
)


def analyze(csv_path, name):

    df = pd.read_csv(
        csv_path
    )

    df["Path"] = df["Path"].astype(str)

    df["View"] = (
        df["Frontal/Lateral"]
        .fillna("Unknown")
    )


    studies = (
        df.groupby(
            ["Patient_ID"],
            dropna=False
        )["View"]
        .apply(set)
    )


    frontal_only = 0
    lateral_only = 0
    paired = 0
    unknown = 0


    for views in studies:

        has_frontal = (
            "Frontal" in views
        )

        has_lateral = (
            "Lateral" in views
        )


        if has_frontal and has_lateral:

            paired += 1

        elif has_frontal:

            frontal_only += 1

        elif has_lateral:

            lateral_only += 1

        else:

            unknown += 1


    print()
    print("=" * 80)

    print(
        name
    )

    print("=" * 80)

    print(
        "Total patients:",
        len(studies)
    )

    print(
        "Patients with frontal + lateral:",
        paired
    )

    print(
        "Frontal only:",
        frontal_only
    )

    print(
        "Lateral only:",
        lateral_only
    )

    print(
        "Unknown only:",
        unknown
    )

    if len(studies) > 0:

        print()

        print(
            "Paired percentage:",
            f"{paired / len(studies) * 100:.2f}%"
        )


print()
print(
    "HC-XCDSS STUDY-LEVEL VIEW ANALYSIS"
)


analyze(
    TRAIN_CSV,
    "TRAINING SET"
)


analyze(
    VALIDATION_CSV,
    "VALIDATION SET"
)


print()
print(
    "=" * 80
)

print(
    "STUDY VIEW ANALYSIS COMPLETED"
)

print(
    "=" * 80
)