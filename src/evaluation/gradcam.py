import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms


# ============================================================
# HC-XCDSS GRAD-CAM EXPLAINABILITY
# ============================================================

sys.path.append("src/models")

from densenet import CheXpertDenseNet


# ============================================================
# CONFIGURATION
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available()
    else "cpu"
)

CHECKPOINT_PATH = (
    "models/checkpoints/"
    "best_densenet121_balanced.pth"
)

DATA_ROOT = Path("data")

OUTPUT_DIR = Path(
    "outputs/evaluation/gradcam"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


TARGETS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion",
]


# ============================================================
# SELECT TEST IMAGE
# ============================================================

TEST_IMAGE = (
    "CheXpert-v1.0-small/train/"
    "patient00007/study1/"
    "view1_frontal.jpg"
)


# ============================================================
# PREPROCESSING
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
# LOAD MODEL
# ============================================================

print()
print("=" * 80)
print("HC-XCDSS GRAD-CAM")
print("=" * 80)

print()
print("Device:", DEVICE)

if torch.cuda.is_available():

    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )


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


print(
    "Checkpoint epoch:",
    checkpoint["epoch"]
)


# ============================================================
# FIND DENSENET LAST CONVOLUTIONAL LAYER
# ============================================================

target_layer = None
target_layer_name = None


for name, module in model.named_modules():

    if isinstance(
        module,
        torch.nn.Conv2d
    ):

        target_layer = module
        target_layer_name = name


if target_layer is None:

    raise RuntimeError(
        "Could not find convolutional layer."
    )


print(
    "Grad-CAM target layer:",
    target_layer_name
)


# ============================================================
# GRAD-CAM STORAGE
# ============================================================

activations = None
gradients = None


def forward_hook(
    module,
    inputs,
    output
):

    global activations

    activations = output


def backward_hook(
    module,
    grad_input,
    grad_output
):

    global gradients

    gradients = grad_output[0]


forward_handle = target_layer.register_forward_hook(
    forward_hook
)

backward_handle = target_layer.register_full_backward_hook(
    backward_hook
)


# ============================================================
# LOAD IMAGE
# ============================================================

image_path = (
    DATA_ROOT
    / Path(TEST_IMAGE).relative_to(
        "CheXpert-v1.0-small"
    )
)


if not image_path.exists():

    forward_handle.remove()
    backward_handle.remove()

    raise FileNotFoundError(
        f"Image not found: {image_path}"
    )


print()
print(
    "Image:",
    TEST_IMAGE
)


original_image = Image.open(
    image_path
).convert(
    "RGB"
)


original_array = np.asarray(
    original_image
)


input_tensor = transform(
    original_image
).unsqueeze(
    0
).to(
    DEVICE
)


# ============================================================
# FORWARD PASS
# ============================================================

model.zero_grad(
    set_to_none=True
)


output = model(
    input_tensor
)


probabilities = torch.sigmoid(
    output
)[0]


print()
print("=" * 80)
print("PREDICTIONS")
print("=" * 80)


for index, target in enumerate(
    TARGETS
):

    probability = float(
        probabilities[index].detach().cpu()
    )

    print(
        f"{target:<20} "
        f"{probability:.4f}"
    )


# ============================================================
# GENERATE GRAD-CAM FOR EACH FINDING
# ============================================================

print()
print("=" * 80)
print("GENERATING GRAD-CAM")
print("=" * 80)


for target_index, target in enumerate(
    TARGETS
):

    print()
    print(
        f"Processing: {target}"
    )


    # --------------------------------------------------------
    # Clear previous gradients
    # --------------------------------------------------------

    model.zero_grad(
        set_to_none=True
    )


    # --------------------------------------------------------
    # Select one class output
    # --------------------------------------------------------

    score = output[
        0,
        target_index
    ]


    # --------------------------------------------------------
    # Backpropagate
    # --------------------------------------------------------

    score.backward(
        retain_graph=True
    )


    # --------------------------------------------------------
    # Read activations and gradients
    # --------------------------------------------------------

    if activations is None:

        raise RuntimeError(
            "Activations were not captured."
        )


    if gradients is None:

        raise RuntimeError(
            "Gradients were not captured."
        )


    activation_map = (
        activations[0]
        .detach()
        .cpu()
        .numpy()
    )


    gradient_map = (
        gradients[0]
        .detach()
        .cpu()
        .numpy()
    )


    # --------------------------------------------------------
    # Global average pooling of gradients
    # --------------------------------------------------------

    weights = np.mean(
        gradient_map,
        axis=(1, 2)
    )


    # --------------------------------------------------------
    # Weighted activation maps
    # --------------------------------------------------------

    cam = np.zeros(
        activation_map.shape[1:],
        dtype=np.float32
    )


    for channel in range(
        activation_map.shape[0]
    ):

        cam += (
            weights[channel]
            *
            activation_map[channel]
        )


    # --------------------------------------------------------
    # ReLU
    # --------------------------------------------------------

    cam = np.maximum(
        cam,
        0
    )


    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    if np.max(cam) > 0:

        cam = (
            cam
            /
            np.max(cam)
        )

    else:

        cam = np.zeros_like(
            cam
        )


    # --------------------------------------------------------
    # Resize heatmap to original image
    # --------------------------------------------------------

    cam = cv2.resize(
        cam,
        (
            original_array.shape[1],
            original_array.shape[0]
        )
    )


    # --------------------------------------------------------
    # Convert to heatmap
    # --------------------------------------------------------

    heatmap = np.uint8(
        255 * cam
    )


    heatmap = cv2.applyColorMap(
        heatmap,
        cv2.COLORMAP_JET
    )


    # OpenCV uses BGR.
    # Original PIL image is RGB.
    original_bgr = cv2.cvtColor(
        original_array,
        cv2.COLOR_RGB2BGR
    )


    # --------------------------------------------------------
    # Overlay
    # --------------------------------------------------------

    overlay = cv2.addWeighted(
        original_bgr,
        0.55,
        heatmap,
        0.45,
        0
    )


    # --------------------------------------------------------
    # Probability
    # --------------------------------------------------------

    probability = float(
        probabilities[
            target_index
        ].detach().cpu()
    )


    # --------------------------------------------------------
    # Save files
    # --------------------------------------------------------

    safe_target = (
        target
        .lower()
        .replace(
            " ",
            "_"
        )
    )


    heatmap_path = (
        OUTPUT_DIR
        /
        f"{safe_target}_heatmap.jpg"
    )


    overlay_path = (
        OUTPUT_DIR
        /
        f"{safe_target}_overlay.jpg"
    )


    cv2.imwrite(
        str(heatmap_path),
        heatmap
    )


    cv2.imwrite(
        str(overlay_path),
        overlay
    )


    print(
        f"Probability: {probability:.4f}"
    )

    print(
        "Heatmap:",
        heatmap_path
    )

    print(
        "Overlay:",
        overlay_path
    )


# ============================================================
# CLEANUP
# ============================================================

forward_handle.remove()
backward_handle.remove()


print()
print("=" * 80)
print("GRAD-CAM COMPLETED")
print("=" * 80)

print()
print(
    "Output directory:"
)

print(
    OUTPUT_DIR
)