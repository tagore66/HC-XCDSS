import torch.nn as nn
from torchvision.models import densenet121, DenseNet121_Weights


class CheXpertDenseNet(nn.Module):

    def __init__(self, num_classes=5):

        super().__init__()

        self.model = densenet121(
            weights=DenseNet121_Weights.DEFAULT
        )

        input_features = self.model.classifier.in_features

        self.model.classifier = nn.Linear(
            input_features,
            num_classes
        )

    def forward(self, x):

        return self.model(x)