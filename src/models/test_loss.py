import torch

from loss import masked_bce_loss


logits = torch.tensor([
    [1.5, -0.5, 0.8, 2.0, -1.0],
    [-0.2, 1.2, -1.5, 0.7, 1.8]
], requires_grad=True)

targets = torch.tensor([
    [1.0, float("nan"), 0.0, 1.0, float("nan")],
    [0.0, 1.0, float("nan"), 1.0, 0.0]
])

mask = ~torch.isnan(targets)

loss = masked_bce_loss(
    logits,
    targets,
    mask
)

loss.backward()

print("Loss:", loss.item())
print("Gradient calculated:", logits.grad is not None)
print("Gradient:")
print(logits.grad)