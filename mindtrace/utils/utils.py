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

import functools
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor


def singleton(cls):
    """Creates a singleton class.

    Repeated calls to create a new instance of the class will return the original instance, even if different arguments
    are passed to the constructor.

    Note that there are many ways to implement a singleton class in Python. Refer to this
    `discussion <https://stackoverflow.com/questions/6760685/what-is-the-best-way-of-implementing-singleton-in-python>`_
    for a breakdown of some of the common methods and if a decorator is the best approach for your current case.

    Example::

        from mtrix import MtrixBase
        from mtrix.utils import singleton

        @singleton
        class MyClass(MtrixBase):
            def __init__(self, name):
                self.name = name

        my_instance_1 = MyClass("instance_1")
        my_instance_2 = MyClass("instance_2")  # Returns my_instance_1

        assert my_instance_1 is my_instance_2
        assert my_instance_1.name == "instance_1"
        assert my_instance_2.name == "instance_1"

    """
    instances = {}

    def getinstance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return getinstance


def singleton_by_args(cls):
    """Creates a singleton class based on the arguments passed to the class constructor.

    This decorator may be used to create singleton classes that are unique based on the arguments passed to the class
    constructor. That is, explicitly:

    - If instances of the same class are created with the same args and kwargs, this decorator will return
    the previously instantiated instance;
    - If instances of the same class are created with different args and/or kwargs, this decorator will create a new
    instance and store it for future reference;
    - This decorator may be used for multiple classes, each with their own unique instances.

    Reference: Siddhesh Sathe's `handy decorators library <https://github.com/siddheshsathe/handy-decorators>`_.

    Example::

        from mtrix import MtrixBase
        from mtrix.utils import singleton_by_args

        @singleton_by_args
        class PostgresConnection(MtrixBase):
            def __init__(self, host: str, port: int):
                self.host = host
                self.port = port

        @singleton_by_args
        class RedisConnection(MtrixBase):
            def __init__(self, host: str, port: int):
                self.host = host
                self.port = port

        pg_connection_1 = PostgresConnection(host="localhost", port=6379)
        pg_connection_2 = PostgresConnection(host="localhost", port=6379)  # Returns pg_connection_1
        pg_connection_3 = PostgresConnection(host="localhost", port=6380)  # Returns new instance
        redis_connection_1 = RedisConnection(host="localhost", port=6379)  # Returns new instance
        redis_connection_2 = RedisConnection(host="localhost", port=6379)  # Returns redis_connection_1

        assert pg_connection_1 is pg_connection_2
        assert pg_connection_1 is not pg_connection_3
        assert redis_connection_1 is not pg_connection_1
        assert redis_connection_1 is redis_connection_2

    """

    previous_instances = {}

    @functools.wraps(cls)
    def wrapper(*args, **kwargs):
        key = (str(cls),) + args + tuple(sorted(kwargs.items()))  # create a unique key for the args and kwargs
        if key not in previous_instances:
            previous_instances[key] = cls(*args, **kwargs)
        return previous_instances[key]

    return wrapper

def multithread(num_threads):
    """
    A decorator that enables multithreading for a function, allowing both 
    single and batch execution using multiple threads.

    The decorator supports:
    1. **Single execution**: Runs normally when normal arguments are passed.
    2. **Batch execution with positional arguments**: Accepts a list of tuples where each tuple 
       contains positional arguments for the function.
    3. **Batch execution with keyword arguments**: Accepts a list of dictionaries where 
       each dictionary represents keyword arguments for the function.
    4. **Explicit batch execution using `tasks` keyword**: The function can also be called 
       with `tasks=` in `kwargs`, which should be a list of dictionaries.

    Example::

    **1. Normal Function Execution (No Multithreading)**
        @multithread(num_threads=4)
        def process_data(x, y, z):
            return {"sum": x + y + z, "product": x * y * z}
        assert process_data(1, 2, 3) is {'sum': 6, 'product': 6}

    **2. Batch Execution with Positional Arguments (Tuples)**
         batch_args = [(1, 2, 3), (4, 5, 6), (7, 8, 9)]
         assert process_data(batch_args) == [{'sum': 6, 'product': 6}, {'sum': 15, 'product': 120}, {'sum': 24, 'product': 504}]

    **3. Batch Execution with Keyword Arguments (Dictionaries)**
         batch_kwargs = [
             {"x": 1, "y": 2, "z": 3},
             {"x": 4, "y": 5, "z": 6},
             {"x": 7, "y": 8, "z": 9}
         ]
         assert process_data(batch_kwargs) == [{'sum': 6, 'product': 6}, {'sum': 15, 'product': 120}, {'sum': 24, 'product': 504}]

    **4. Batch Execution Using the `tasks` Keyword**
         assert process_data(tasks=batch_kwargs) == [{'sum': 6, 'product': 6}, {'sum': 15, 'product': 120}, {'sum': 24, 'product': 504}]

    Args:
        num_threads (int): The number of threads to use for parallel execution.

    Returns:
        function: A wrapped function that supports both normal and parallel execution.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):

            # If only one argument is passed and it's iterable, apply threading
            if len(args) == 1 and isinstance(args[0], Iterable) and not isinstance(args[0], (str, bytes, dict)):
                inputs = args[0]  # List of positional argument tuples
                if all(isinstance(arg, dict) for arg in inputs):
                    with ThreadPoolExecutor(max_workers=num_threads) as executor:
                        results = list(executor.map(lambda kw: func(**kw), inputs))
                        return results
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    results = list(executor.map(lambda arg_tuple: func(*arg_tuple), inputs))
                return results
            # If kwargs contain batch processing information
            elif 'tasks' in kwargs and isinstance(kwargs['tasks'], list):
                tasks = kwargs['tasks']  # List of dicts for kwargs
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    results = list(executor.map(lambda kw: func(**kw), tasks))
                return results

            # Normal function execution (single call)
            return func(*args, **kwargs)

        return wrapper
    return decorator
