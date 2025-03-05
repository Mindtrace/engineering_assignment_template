from typing import Union

import numpy as np
from PIL.Image import Image
import torch
from torch import nn

from mindtrace.utils import ifnone, pil_to_tensor


class MLPModule(nn.Module):
    """A simple multi-layer perceptron (MLP) model.

    Args:
        dim: List of layer dimensions. Defaults to [784, 100, 10].
        dropout: Dropout probability. Defaults to 0.2.
    """
    def __init__(self, dim: list[int] | None = None, dropout: float = 0.2, **_):
        super().__init__()
        dim = ifnone(dim, default=[784, 100, 10])
        layers = []
        for i in range(len(dim) - 1):
            layers.append(nn.Linear(dim[i], dim[i + 1]))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
        self.model = nn.Sequential(*layers)

    def __call__(self, image: Union[Image, np.ndarray, torch.Tensor]):
        if isinstance(image, np.ndarray):
            image = torch.Tensor(image).float()
        elif isinstance(image, Image):
            image = pil_to_tensor(image).float()
        elif not isinstance(image, torch.Tensor):
            raise TypeError(f"Expected image to be of type Image, np.ndarray, or torch.Tensor, but got {type(image)}.")
        prediction = torch.softmax(self.forward(image), dim=1)
        return prediction

    def forward(self, x: torch.Tensor):
        if len(x.shape) == 3:
            x = x.unsqueeze(0)
        return self.model(x.reshape(x.shape[0], -1))
