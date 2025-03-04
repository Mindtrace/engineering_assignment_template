import base64
import io
import os

import PIL
from PIL.Image import Image
import torch
from torchvision.transforms.v2 import functional as F


def ifnone(val: any, default: any):
    """Return the given value if it is not None, else return the default."""
    return val if val is not None else default


def available_cores():
    """Returns the number of cores available to the current process."""
    try:
        return len(os.sched_getaffinity(0))  # Not currently supported for Windows
    except AttributeError:
        return num_cores()


def num_cores():
    """Returns the number of cores visible to the OS."""
    return os.cpu_count()


def flatten_dict(nested_dict: dict[str, any], parent_key: str = "", sep: str = ".") -> dict[str, any]:
    """Flatten a nested dictionary.

    Args:
        nested_dict: The dictionary to flatten.
        parent_key: The base key string for the flattened keys.
        sep: The separator between parent and child keys.

    Returns:
        Dict[str, any]: A flattened dictionary with concatenated keys.

    Example::

        from mindtrace.utils import flatten_dict

        nested = {
             "a": 1,
             "b": {
                 "c": 2,
                 "d": {
                     "e": 3
                 }
             }
         }
        flatten_dict(nested)  # {'a': 1, 'b.c': 2, 'b.d.e': 3}
        flatten_dict(nested, sep="_")  # {'a': 1, 'b_c': 2, 'b_d_e': 3}
        flatten_dict(nested, parent_key="root", sep="->")  # {'root->a': 1, 'root->b->c': 2, 'root->b->d->e': 3}
    """
    items = []
    for k, v in nested_dict.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def pil_to_ascii(image: Image) -> str:
    """Serialize PIL Image to ascii.

    Example::

          import PIL
          from mindtrace.utils import pil_to_ascii, ascii_to_pil

          image = PIL.Image.open('tests/resources/hopper.png')
          ascii_image = pil_to_ascii(image)
          decoded_image = ascii_to_pil(ascii_image)
    """
    imageio = io.BytesIO()
    image.save(imageio, "png")
    bytes_image = base64.b64encode(imageio.getvalue())
    ascii_image = bytes_image.decode("ascii")
    return ascii_image


def ascii_to_pil(ascii_image: str) -> Image:
    """Convert ascii image to PIL Image.

    Example::

          import PIL
          from mindtrace.utils import pil_to_ascii, ascii_to_pil

          image = PIL.Image.open('tests/resources/hopper.png')
          ascii_image = pil_to_ascii(image)
          decoded_image = ascii_to_pil(ascii_image)
    """
    return PIL.Image.open(io.BytesIO(base64.b64decode(ascii_image)))


def pil_to_tensor(image: Image) -> torch.Tensor:
    """Convert PIL Image to Torch Tensor.

    Example::

        from PIL import Image
        from mindtrace.utils import pil_to_tensor

        image = Image.open('tests/resources/hopper.png')
        tensor = pil_to_tensor(image)
    """
    return F.pil_to_tensor(image)


def tensor_to_pil(image: torch.Tensor, mode=None, min_val=None, max_val=None) -> Image:
    """Convert Torch Tensor to PIL Image.

    Note that PIL float images must be scaled [0, 1]. It is often the case, however, that torch tensor images may have a
    different range (e.g. zero mean or [-1, 1]). As such, the input torch tensor will automatically be scaled to fit in
    the range [0, 1]. If no min / max value is provided, the output range will be identically 0 / 1, respectively. Else
    you may pass in min / max range values explicitly.

    Args:
        image: The input image.
        mode: The mode of the *output* image. One of {'L', 'RGB', 'RGBA'}.
        min_val: The minimum value of the input image. If None, it will be inferred from the input image.
        max_val: The maximum value of the input image. If None, it will be inferred from the input image.

    Example::

        from PIL import Image
        from mindtrace.utils import pil_to_tensor, tensor_to_pil

        image = Image.open('tests/resources/hopper.png')
        tensor_image = pil_to_tensor(image)
        pil_image = tensor_to_pil(tensor_image)
    """
    min_ = min_val if min_val is not None else torch.min(image)
    max_ = max_val if max_val is not None else torch.max(image)
    return F.to_pil_image((image - min_) / (max_ - min_), mode=mode)
