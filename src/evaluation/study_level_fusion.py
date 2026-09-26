import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from torchvision import transforms
from PIL import Image

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    recall_score,
    confusion_matrix
)


sys.path.append("src/models")

from densenet import CheXpertDenseNet


# ============================================================
# CONFIGURATION
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available()
    else "cpu"
)

BATCH_SIZE = 8

VALIDATION_CSV = (
    "data/splits/validation_clean.csv"
)

CHECKPOINT_PATH = (
    "models/checkpoints/"
    "best_densenet121_balanced.pth"
)

VIEW_THRESHOLD_PATH = (
    "outputs/evaluation/"
    "view_specific_thresholds.json"
)

DATA_ROOT = Path("data")

OUTPUT_PATH = (
    "outputs/evaluation/"
    "study_level_predictions.csv"
)


TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion"
]


# ============================================================
# FINAL FUSION STRATEGIES
# Based on previous study-level validation
# ============================================================

FUSION_STRATEGIES = {

    "Atelectasis": "max",

    "Cardiomegaly": "max",

    "Consolidation": "mean",

    "Edema": "max",

    "Pleural Effusion": "max"
}


# ============================================================
# HEADER
# ============================================================

print()
print("=" * 80)
print("HC-XCDSS FINAL STUDY-LEVEL FUSION")
print("=" * 80)

print()
print("Device:", DEVICE)

if torch.cuda.is_available():

    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )


# ============================================================
# LOAD VIEW-SPECIFIC THRESHOLDS
# ============================================================

with open(
    VIEW_THRESHOLD_PATH,
    "r"
) as file:

    view_threshold_data = json.load(file)


# Extract ONLY the optimal thresholds.
#
# JSON structure:
#
# target
#   -> Frontal
#       -> optimal_threshold
#
#   -> Lateral
#       -> optimal_threshold
#
# ============================================================

view_thresholds = {}

for target in TARGETS:

    view_thresholds[target] = {

        "Frontal":
            float(
                view_threshold_data[target]
                ["Frontal"]
                ["optimal_threshold"]
            ),

        "Lateral":
            float(
                view_threshold_data[target]
                ["Lateral"]
                ["optimal_threshold"]
            )
    }


print()
print("VIEW-SPECIFIC THRESHOLDS")
print("-" * 80)

for target in TARGETS:

    print(
        f"{target}: "
        f"Frontal={view_thresholds[target]['Frontal']:.2f} "
        f"Lateral={view_thresholds[target]['Lateral']:.2f}"
    )


# ============================================================
# FUSION STRATEGIES
# ============================================================

print()
print("FINAL FUSION STRATEGIES")
print("-" * 80)

for target in TARGETS:

    print(
        f"{target}: "
        f"{FUSION_STRATEGIES[target].upper()}"
    )


# ============================================================
# TRANSFORM
# ============================================================

transform = transforms.Compose([

    transforms.Resize(
        (224, 224)
    ),

    transforms.ToTensor(),

    transforms.Normalize(

        mean=[
            0.485,
            0.456,
            0.406
        ],

        std=[
            0.229,
            0.224,
            0.225
        ]
    )
])


# ============================================================
# LOAD VALIDATION DATA
# ============================================================

df = pd.read_csv(
    VALIDATION_CSV
)

df["Path"] = df["Path"].astype(str)


# ============================================================
# CREATE STUDY ID
# ============================================================

def get_study_id(path):

    parts = Path(path).parts

    patient_id = None
    study_id = None

    for part in parts:

        if part.startswith("patient"):

            patient_id = part

        elif part.startswith("study"):

            study_id = part


    if (
        patient_id is None
        or study_id is None
    ):

        return None


    return (
        patient_id,
        study_id
    )


df["Study_ID"] = df["Path"].apply(
    get_study_id
)

df = df[
    df["Study_ID"].notna()
].copy()


print()
print(
    "Validation images:",
    len(df)
)

print(
    "Unique studies:",
    df["Study_ID"].nunique()
)


# ============================================================
# STUDY LABEL CONSISTENCY
# ============================================================

print()
print("=" * 80)
print("STUDY LABEL CONSISTENCY")
print("=" * 80)


for target in TARGETS:

    inconsistent = 0

    for study_id, group in df.groupby(
        "Study_ID"
    ):

        values = group[target].dropna()

        values = values[
            values.isin([0.0, 1.0])
        ]

        if len(values) == 0:

            continue

        if values.nunique() > 1:

            inconsistent += 1


    print(
        f"{target}: "
        f"{inconsistent} inconsistent studies"
    )


# ============================================================
# LOAD MODEL
# ============================================================

model = CheXpertDenseNet(
    num_classes=5
).to(
    DEVICE
)


checkpoint = torch.load(
    CHECKPOINT_PATH,
    map_location=DEVICE
)


model.load_state_dict(
    checkpoint["model_state_dict"]
)

model.eval()


print()
print(
    "Checkpoint epoch:",
    checkpoint["epoch"]
)

print(
    "Checkpoint validation loss:",
    checkpoint["validation_loss"]
)


# ============================================================
# IMAGE-LEVEL PREDICTIONS
# ============================================================

print()
print("=" * 80)
print("GENERATING IMAGE-LEVEL PREDICTIONS")
print("=" * 80)


predictions = []

paths = df["Path"].tolist()


with torch.no_grad():

    for start in range(
        0,
        len(paths),
        BATCH_SIZE
    ):

        batch_paths = paths[
            start:
            start + BATCH_SIZE
        ]


        images = []


        for path in batch_paths:

            image_path = (
                DATA_ROOT
                / Path(path).relative_to(
                    "CheXpert-v1.0-small"
                )
            )


            try:

                image = Image.open(
                    image_path
                ).convert("RGB")


                image = transform(
                    image
                )

                images.append(
                    image
                )


            except Exception as error:

                print(
                    "ERROR:",
                    path,
                    error
                )

                images.append(
                    torch.zeros(
                        3,
                        224,
                        224
                    )
                )


        images = torch.stack(
            images
        ).to(
            DEVICE,
            non_blocking=True
        )


        outputs = model(
            images
        )


        probabilities = torch.sigmoid(
            outputs
        ).cpu().numpy()


        predictions.append(
            probabilities
        )


        processed = min(
            start + BATCH_SIZE,
            len(paths)
        )


        if processed % 1000 < BATCH_SIZE:

            print(
                f"Processed: {processed}"
            )


predictions = np.concatenate(
    predictions,
    axis=0
)


print()
print(
    "Predictions generated:",
    len(predictions)
)


# ============================================================
# ADD PREDICTION INDEX
# ============================================================

df["prediction_index"] = np.arange(
    len(df)
)


# ============================================================
# BUILD STUDY-LEVEL PREDICTIONS
# ============================================================

print()
print("=" * 80)
print("BUILDING STUDY-LEVEL PREDICTIONS")
print("=" * 80)


study_records = []


for study_id, group in df.groupby(
    "Study_ID"
):

    indices = group[
        "prediction_index"
    ].values


    group_predictions = predictions[
        indices
    ]


    frontal_mask = (
        group["Frontal/Lateral"]
        .values
        == "Frontal"
    )


    lateral_mask = (
        group["Frontal/Lateral"]
        .values
        == "Lateral"
    )


    frontal_predictions = (
        group_predictions[
            frontal_mask
        ]
    )


    lateral_predictions = (
        group_predictions[
            lateral_mask
        ]
    )


    # We need at least one frontal image.
    if len(frontal_predictions) == 0:

        continue


    record = {

        "Study_ID":
            str(study_id),

        "frontal_count":
            len(frontal_predictions),

        "lateral_count":
            len(lateral_predictions)
    }


    # ========================================================
    # FINDINGS
    # ========================================================

    for target_index, target in enumerate(
        TARGETS
    ):

        # ----------------------------------------------------
        # Frontal predictions
        # ----------------------------------------------------

        frontal_scores = (
            frontal_predictions[
                :,
                target_index
            ]
        )


        frontal_score = float(
            np.max(
                frontal_scores
            )
        )


        # ----------------------------------------------------
        # Lateral predictions
        # ----------------------------------------------------

        if len(lateral_predictions) > 0:

            lateral_scores = (
                lateral_predictions[
                    :,
                    target_index
                ]
            )


            lateral_score = float(
                np.max(
                    lateral_scores
                )
            )

        else:

            lateral_scores = np.array([])

            lateral_score = np.nan


        # ----------------------------------------------------
        # Combined scores
        # ----------------------------------------------------

        if len(lateral_scores) > 0:

            all_scores = np.concatenate(
                [
                    frontal_scores,
                    lateral_scores
                ]
            )

        else:

            all_scores = frontal_scores


        max_score = float(
            np.max(
                all_scores
            )
        )


        mean_score = float(
            np.mean(
                all_scores
            )
        )


        # ----------------------------------------------------
        # Selected strategy
        # ----------------------------------------------------

        strategy = FUSION_STRATEGIES[
            target
        ]


        if strategy == "frontal":

            final_score = frontal_score


        elif strategy == "max":

            final_score = max_score


        elif strategy == "mean":

            final_score = mean_score


        else:

            raise ValueError(
                f"Unknown fusion strategy: "
                f"{strategy}"
            )


        # ----------------------------------------------------
        # Study label
        # ----------------------------------------------------

        study_labels = group[target].dropna()

        study_labels = study_labels[
            study_labels.isin(
                [0.0, 1.0]
            )
        ]


        if len(study_labels) > 0:

            study_label = int(
                study_labels.iloc[0]
            )

        else:

            study_label = np.nan


        # ----------------------------------------------------
        # Store scores
        # ----------------------------------------------------

        record[
            f"{target}_label"
        ] = study_label


        record[
            f"{target}_frontal"
        ] = frontal_score


        record[
            f"{target}_lateral"
        ] = lateral_score


        record[
            f"{target}_max"
        ] = max_score


        record[
            f"{target}_mean"
        ] = mean_score


        record[
            f"{target}_strategy"
        ] = strategy


        record[
            f"{target}_score"
        ] = final_score


        # ----------------------------------------------------
        # Store thresholds
        # ----------------------------------------------------

        frontal_threshold = (
            view_thresholds[
                target
            ]["Frontal"]
        )


        lateral_threshold = (
            view_thresholds[
                target
            ]["Lateral"]
        )


        record[
            f"{target}_frontal_threshold"
        ] = frontal_threshold


        record[
            f"{target}_lateral_threshold"
        ] = lateral_threshold


        # ----------------------------------------------------
        # STUDY OPERATING THRESHOLD
        #
        # For studies containing a frontal view, use the
        # frontal threshold as the primary study threshold.
        #
        # This is appropriate because every retained study
        # has at least one frontal image and frontal is the
        # dominant clinical view.
        # ----------------------------------------------------

        study_threshold = (
            frontal_threshold
        )


        record[
            f"{target}_threshold"
        ] = study_threshold


        record[
            f"{target}_prediction"
        ] = int(
            final_score >= study_threshold
        )


    study_records.append(
        record
    )


study_df = pd.DataFrame(
    study_records
)


print()
print(
    "Studies:",
    len(study_df)
)


# ============================================================
# FINAL STUDY-LEVEL EVALUATION
# ============================================================

print()
print("=" * 80)
print("FINAL STUDY-LEVEL FUSION RESULTS")
print("=" * 80)


for target in TARGETS:

    print()
    print("-" * 80)
    print(target)
    print("-" * 80)


    strategy = FUSION_STRATEGIES[
        target
    ]


    labels = study_df[
        f"{target}_label"
    ].values


    scores = study_df[
        f"{target}_score"
    ].values


    threshold = float(
        study_df[
            f"{target}_threshold"
        ].iloc[0]
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


    y_pred = (
        y_score >= threshold
    ).astype(int)


    if len(
        np.unique(y_true)
    ) < 2:

        print(
            "Insufficient class variation."
        )

        continue


    auc = roc_auc_score(
        y_true,
        y_score
    )


    pr_auc = average_precision_score(
        y_true,
        y_score
    )


    f1 = f1_score(
        y_true,
        y_pred,
        zero_division=0
    )


    sensitivity = recall_score(
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
        if tn + fp > 0
        else 0
    )


    precision = (
        tp / (tp + fp)
        if tp + fp > 0
        else 0
    )


    print(
        f"Fusion strategy: "
        f"{strategy.upper()}"
    )


    print(
        f"Samples:          "
        f"{len(y_true)}"
    )


    print(
        f"Threshold:        "
        f"{threshold:.2f}"
    )


    print(
        f"ROC-AUC:          "
        f"{auc:.4f}"
    )


    print(
        f"PR-AUC:           "
        f"{pr_auc:.4f}"
    )


    print(
        f"Precision:        "
        f"{precision:.4f}"
    )


    print(
        f"Sensitivity:      "
        f"{sensitivity:.4f}"
    )


    print(
        f"Specificity:      "
        f"{specificity:.4f}"
    )


    print(
        f"F1:               "
        f"{f1:.4f}"
    )


    print(
        f"TN: {tn}  "
        f"FP: {fp}  "
        f"FN: {fn}  "
        f"TP: {tp}"
    )


# ============================================================
# SAVE
# ============================================================

Path(
    OUTPUT_PATH
).parent.mkdir(
    parents=True,
    exist_ok=True
)


study_df.to_csv(
    OUTPUT_PATH,
    index=False
)


print()
print(
    "Study-level predictions saved:"
)

print(
    OUTPUT_PATH
)


print()
print("=" * 80)
print(
    "FINAL STUDY-LEVEL FUSION COMPLETED"
)
print("=" * 80)