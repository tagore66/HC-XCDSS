# --------------------------------------------------
# Patient-friendly explanations
# --------------------------------------------------

FINDING_EXPLANATIONS = {

    "Atelectasis": {
        "title": "Atelectasis",

        "simple": (
            "The X-ray shows an area of the lung "
            "that may not be fully expanded."
        ),

        "what_it_means": (
            "Atelectasis means that part of the lung "
            "appears less expanded than usual on the "
            "X-ray. It can happen for several different "
            "reasons."
        ),

        "possible_causes": [
            "Shallow breathing",
            "Mucus blocking part of an airway",
            "Pressure on the lung",
            "After certain medical procedures or surgery"
        ],

        "important": (
            "This X-ray finding does not by itself "
            "identify the exact cause."
        )
    },


    "Cardiomegaly": {
        "title": "Cardiomegaly",

        "simple": (
            "The heart appears larger than expected "
            "on the X-ray."
        ),

        "what_it_means": (
            "Cardiomegaly means that the heart silhouette "
            "appears enlarged on the X-ray."
        ),

        "possible_causes": [
            "Heart-related conditions",
            "High blood pressure over time",
            "Certain heart muscle problems",
            "Sometimes the appearance can be affected "
            "by how the X-ray was taken"
        ],

        "important": (
            "An enlarged appearance on an X-ray does "
            "not by itself determine the exact heart "
            "condition."
        )
    },


    "Consolidation": {
        "title": "Consolidation",

        "simple": (
            "An area of the lung appears denser than "
            "usual on the X-ray."
        ),

        "what_it_means": (
            "Consolidation describes an area of the lung "
            "that appears more opaque or dense than "
            "normal on the X-ray."
        ),

        "possible_causes": [
            "Infection",
            "Inflammation",
            "Fluid or other material within the lung"
        ],

        "important": (
            "The X-ray appearance alone cannot determine "
            "the exact cause."
        )
    },


    "Edema": {
        "title": "Edema",

        "simple": (
            "The X-ray shows signs that may indicate "
            "extra fluid in the lungs."
        ),

        "what_it_means": (
            "Pulmonary edema refers to excess fluid "
            "within the lung tissues or air spaces."
        ),

        "possible_causes": [
            "Some heart-related conditions",
            "Fluid overload",
            "Certain other medical conditions"
        ],

        "important": (
            "The model identifies an X-ray pattern. "
            "It cannot determine the underlying cause "
            "from the X-ray alone."
        )
    },


    "Pleural Effusion": {
        "title": "Pleural Effusion",

        "simple": (
            "The X-ray shows signs that may indicate "
            "extra fluid around the lung."
        ),

        "what_it_means": (
            "A pleural effusion is extra fluid in the "
            "space between the lung and the chest wall."
        ),

        "possible_causes": [
            "Heart-related conditions",
            "Infection",
            "Inflammation",
            "Other medical conditions"
        ],

        "important": (
            "There are many possible causes, and an "
            "X-ray alone cannot determine which cause "
            "is responsible."
        )
    }
}


# --------------------------------------------------
# Get explanation
# --------------------------------------------------

def get_finding_explanation(
    finding
):

    if finding not in FINDING_EXPLANATIONS:

        raise ValueError(
            f"Unknown finding: {finding}"
        )


    return FINDING_EXPLANATIONS[
        finding
    ]


# --------------------------------------------------
# Build patient-friendly result
# --------------------------------------------------

def build_patient_explanation(
    findings
):

    explanations = []


    for finding, result in findings.items():

        if not result["detected"]:

            continue


        explanation = (
            get_finding_explanation(
                finding
            )
        )


        explanations.append({

            "finding":
                finding,

            "title":
                explanation["title"],

            "simple_explanation":
                explanation["simple"],

            "what_it_means":
                explanation["what_it_means"],

            "possible_causes":
                explanation["possible_causes"],

            "important_note":
                explanation["important"]
        })


    return explanations