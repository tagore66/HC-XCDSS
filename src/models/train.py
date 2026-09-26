import torch
from torch.utils.data import DataLoader
from torchvision import transforms

from densenet import CheXpertDenseNet
from loss import masked_bce_loss

import sys

sys.path.append("src/data")

from dataset import CheXpertDataset


device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("Device:", device)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))


transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


dataset = CheXpertDataset(
    "data/splits/train_clean.csv",
    transform=transform
)


loader = DataLoader(
    dataset,
    batch_size=8,
    shuffle=True,
    num_workers=0,
    pin_memory=True
)


model = CheXpertDenseNet(
    num_classes=5
).to(device)


optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=1e-4,
    weight_decay=1e-4
)


model.train()

running_loss = 0.0

for batch_index, (images, labels, masks) in enumerate(loader):

    images = images.to(
        device,
        non_blocking=True
    )

    labels = labels.to(
        device,
        non_blocking=True
    )

    masks = masks.to(
        device,
        non_blocking=True
    )

    optimizer.zero_grad()

    outputs = model(images)

    loss = masked_bce_loss(
        outputs,
        labels,
        masks
    )

    loss.backward()

    optimizer.step()

    running_loss += loss.item()

    if (batch_index + 1) % 10 == 0:

        average_loss = (
            running_loss / 10
        )

        print(
            f"Batch {batch_index + 1} "
            f"Loss: {average_loss:.4f}"
        )

        running_loss = 0.0

    if batch_index == 49:
        break


print("Smoke test training completed.")