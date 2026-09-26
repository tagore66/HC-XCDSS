import torch

from densenet import CheXpertDenseNet


device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

model = CheXpertDenseNet()

model = model.to(device)

x = torch.randn(
    8,
    3,
    224,
    224
).to(device)

output = model(x)

print("Device:", device)
print("Input shape:", x.shape)
print("Output shape:", output.shape)