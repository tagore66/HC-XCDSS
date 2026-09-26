import sys
import json
import shutil
import uuid

from pathlib import Path

from PIL import Image

from predictor import XRayPredictor
from explainer import XRayExplainer
from validator import xray_validator


# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(
    __file__
).resolve().parents[2]


# --------------------------------------------------
# Explanation module
# --------------------------------------------------

sys.path.append(
    str(
        PROJECT_ROOT
        / "src"
        / "explanation"
    )
)

from finding_explanations import (
    build_patient_explanation
)


# --------------------------------------------------
# Output root directory
# --------------------------------------------------

OUTPUT_ROOT = (
    PROJECT_ROOT
    / "outputs"
    / "analyses"
)


# --------------------------------------------------
# X-ray inference service
# --------------------------------------------------

class XRayInferenceService:

    def __init__(self):

        print(
            "Initializing X-ray inference service..."
        )


        # ------------------------------------------
        # ML predictor
        # ------------------------------------------

        self.predictor = XRayPredictor()


        # ------------------------------------------
        # Grad-CAM explainer
        # ------------------------------------------

        self.explainer = XRayExplainer()


        # ------------------------------------------
        # Chest X-ray Domain Validator Gate
        # ------------------------------------------

        self.validator = xray_validator


        # ------------------------------------------
        # Output directory
        # ------------------------------------------

        OUTPUT_ROOT.mkdir(
            parents=True,
            exist_ok=True
        )


        print(
            "Inference service ready."
        )


    # --------------------------------------------------
    # Create unique analysis directory
    # --------------------------------------------------

    def create_analysis_directory(self):

        analysis_id = uuid.uuid4().hex[:12]


        analysis_directory = (
            OUTPUT_ROOT
            / analysis_id
        )


        analysis_directory.mkdir(
            parents=True,
            exist_ok=False
        )


        return (
            analysis_id,
            analysis_directory
        )


    # --------------------------------------------------
    # Run complete inference
    # --------------------------------------------------

    def analyze(
        self,
        image_path,
        view="Frontal",
        output_directory=None
    ):

        image_path = Path(
            image_path
        )


        if not image_path.exists():

            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )


        # ------------------------------------------
        # Normalize view
        # ------------------------------------------

        view = (
            str(view)
            .strip()
            .capitalize()
        )


        if view not in {
            "Frontal",
            "Lateral"
        }:

            raise ValueError(
                "View must be either "
                "'Frontal' or 'Lateral'."
            )


        # ------------------------------------------
        # Pre-Inference Chest X-Ray Validation Gate
        # ------------------------------------------

        is_valid, rejection_reason, validation_details = self.validator.validate(
            image_path,
            view=view
        )

        if not is_valid:
            raise ValueError(
                f"Input domain validation failed: {rejection_reason}"
            )


        # ------------------------------------------
        # Create analysis directory
        # ------------------------------------------

        if output_directory is None:

            (
                analysis_id,
                analysis_directory
            ) = (
                self.create_analysis_directory()
            )

        else:

            analysis_directory = Path(
                output_directory
            )

            analysis_directory.mkdir(
                parents=True,
                exist_ok=True
            )

            analysis_id = (
                analysis_directory.name
            )


        print()
        print(
            "Analysis ID:"
        )

        print(
            analysis_id
        )


        print(
            "Analysis directory:"
        )

        print(
            analysis_directory
        )


        # ------------------------------------------
        # Copy uploaded X-ray into analysis folder
        # ------------------------------------------

        stored_image_path = (
            analysis_directory
            / (
                "uploaded_xray"
                + image_path.suffix.lower()
            )
        )


        shutil.copy2(
            image_path,
            stored_image_path
        )


        print()
        print(
            "Stored X-ray:"
        )

        print(
            stored_image_path
        )


        # ------------------------------------------
        # Step 1: Model prediction
        # ------------------------------------------

        prediction_result = (
            self.predictor.predict(
                stored_image_path,
                view=view
            )
        )


        findings = (
            prediction_result[
                "findings"
            ]
        )


        # ------------------------------------------
        # Step 2: Generate Grad-CAM
        #
        # ONLY for detected findings
        # ------------------------------------------

        heatmaps = {}


        for finding, result in findings.items():

            if not result["detected"]:

                continue


            print()
            print(
                f"Generating Grad-CAM: "
                f"{finding}"
            )


            heatmap = (
                self.explainer.generate_heatmap(
                    stored_image_path,
                    finding
                )
            )


            filename = (
                finding
                .lower()
                .replace(
                    " ",
                    "_"
                )
                + "_gradcam.jpg"
            )


            heatmap_path = (
                analysis_directory
                / filename
            )


            # --------------------------------------
            # Save heatmap
            # --------------------------------------

            Image.fromarray(
                heatmap
            ).save(
                heatmap_path
            )


            heatmaps[finding] = (
                str(
                    heatmap_path
                )
            )


            print(
                "Saved:"
            )

            print(
                heatmap_path
            )


        # ------------------------------------------
        # Step 3: Attach heatmaps to findings
        # ------------------------------------------

        for finding in findings:

            if finding in heatmaps:

                findings[finding][
                    "heatmap"
                ] = heatmaps[finding]

            else:

                findings[finding][
                    "heatmap"
                ] = None


        # ------------------------------------------
        # Step 4: Build patient explanations
        # ------------------------------------------

        patient_explanations = (
            build_patient_explanation(
                findings
            )
        )


        # ------------------------------------------
        # Step 5: Build detected findings
        # ------------------------------------------

        detected_findings = [

            finding

            for finding, data
            in findings.items()

            if data["detected"]
        ]


        # ------------------------------------------
        # Step 6: Build final response
        # ------------------------------------------

        result = {

            "analysis_id":
                analysis_id,

            "image":
                str(
                    stored_image_path
                ),

            "view":
                view,

            "findings":
                findings,

            "detected_findings":
                detected_findings,

            "heatmaps":
                heatmaps,

            "patient_explanations":
                patient_explanations
        }


        # ------------------------------------------
        # Step 7: Save analysis JSON
        # ------------------------------------------

        result_path = (
            analysis_directory
            / "analysis_result.json"
        )


        with open(
            result_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                result,
                file,
                indent=4
            )


        print()
        print(
            "Analysis JSON saved:"
        )

        print(
            result_path
        )


        print()
        print(
            "=" * 75
        )

        print(
            "ANALYSIS COMPLETED"
        )

        print(
            "=" * 75
        )


        return result


# --------------------------------------------------
# Standalone test
# --------------------------------------------------

if __name__ == "__main__":

    test_image = (
        PROJECT_ROOT
        / "data"
        / "train"
        / "patient00007"
        / "study1"
        / "view1_frontal.jpg"
    )


    service = (
        XRayInferenceService()
    )


    print()
    print(
        "=" * 75
    )

    print(
        "RUNNING COMPLETE X-RAY ANALYSIS"
    )

    print(
        "=" * 75
    )


    result = (
        service.analyze(
            test_image,
            view="Frontal"
        )
    )


    # ------------------------------------------
    # Print analysis ID
    # ------------------------------------------

    print()
    print(
        "ANALYSIS ID:"
    )

    print(
        f"  {result['analysis_id']}"
    )


    # ------------------------------------------
    # Print view
    # ------------------------------------------

    print()
    print(
        "X-RAY VIEW:"
    )

    print(
        f"  {result['view']}"
    )


    # ------------------------------------------
    # Print findings
    # ------------------------------------------

    print()
    print(
        "=" * 75
    )

    print(
        "FINAL FINDINGS"
    )

    print(
        "=" * 75
    )


    for finding, data in (
        result["findings"].items()
    ):

        print()
        print(
            finding
        )

        print(
            f"  Probability: "
            f"{data['probability']:.4f}"
        )

        print(
            f"  Threshold:   "
            f"{data['threshold']:.2f}"
        )

        print(
            f"  Detected:    "
            f"{data['detected']}"
        )

        print(
            f"  Heatmap:     "
            f"{data['heatmap']}"
        )


    # ------------------------------------------
    # Detected findings
    # ------------------------------------------

    print()
    print(
        "=" * 75
    )

    print(
        "DETECTED FINDINGS"
    )

    print(
        "=" * 75
    )


    if result["detected_findings"]:

        for finding in (
            result["detected_findings"]
        ):

            print(
                f"- {finding}"
            )

    else:

        print(
            "No findings detected."
        )


    # ------------------------------------------
    # Patient-friendly explanations
    # ------------------------------------------

    print()
    print(
        "=" * 75
    )

    print(
        "PATIENT-FRIENDLY EXPLANATIONS"
    )

    print(
        "=" * 75
    )


    if result[
        "patient_explanations"
    ]:

        for explanation in (
            result[
                "patient_explanations"
            ]
        ):

            print()
            print(
                explanation[
                    "title"
                ]
            )

            print(
                "  Explanation:"
            )

            print(
                "  "
                + explanation[
                    "simple_explanation"
                ]
            )

            print()
            print(
                "  What it means:"
            )

            print(
                "  "
                + explanation[
                    "what_it_means"
                ]
            )

            print()
            print(
                "  Possible causes:"
            )

            for cause in (
                explanation[
                    "possible_causes"
                ]
            ):

                print(
                    f"    - {cause}"
                )

            print()
            print(
                "  Important:"
            )

            print(
                "  "
                + explanation[
                    "important_note"
                ]
            )


    else:

        print(
            "No detected findings "
            "require explanation."
        )


    print()
    print(
        "=" * 75
    )

    print(
        "COMPLETE INFERENCE TEST COMPLETED"
    )

    print(
        "=" * 75
    )