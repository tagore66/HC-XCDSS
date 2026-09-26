import torch
import torch.nn.functional as F


POSITIVE_WEIGHTS = torch.tensor([
    0.5201,
    0.7059,
    1.4557,
    0.7002,
    0.7054
])


NEGATIVE_WEIGHTS = torch.tensor([
    12.9250,
    1.7144,
    0.7616,
    1.7486,
    1.7173
])


def masked_balanced_bce_loss(
    logits,
    targets,
    mask
):

    targets = targets.clone()

    targets[targets == -1] = 0

    safe_targets = torch.nan_to_num(
        targets,
        nan=0.0
    )


    positive_weights = (
        POSITIVE_WEIGHTS
        .to(logits.device)
        .view(1, -1)
    )

    negative_weights = (
        NEGATIVE_WEIGHTS
        .to(logits.device)
        .view(1, -1)
    )


    weights = torch.where(
        safe_targets == 1,
        positive_weights,
        negative_weights
    )


    loss = F.binary_cross_entropy_with_logits(
        logits,
        safe_targets,
        reduction="none"
    )


    loss = loss * weights

    loss = loss * mask.float()


    valid_count = mask.sum()


    if valid_count == 0:

        return torch.tensor(
            0.0,
            device=logits.device,
            requires_grad=True
        )


    return loss.sum() / valid_count