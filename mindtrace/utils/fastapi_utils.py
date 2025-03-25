from functools import wraps
import importlib
import logging
import time
import traceback
from typing import Any, Callable, Optional, Type

from tqdm import tqdm

from mindtrace.utils import ifnone


def autolog(
        log_level=logging.DEBUG,
        prefix_formatter: Optional[Callable] = None,
        suffix_formatter: Optional[Callable] = None,
        exception_formatter: Optional[Callable] = None,
        self: Optional[Any] = None,
):
    """Decorator that adds logger.log calls to the decorated method before and after the method is called.

    By default, the autolog decorator will log the method name, arguments and keyword arguments before the method
    is called, and the method name and result after the method completes. This behavior can be modified by passing
    in prefix and suffix formatters.

    The autolog decorator will also catch and log all Exceptions, re-raising any exception after logging it. The
    behavior for autologging exceptions can be modified by passing in an exception_formatter.

    The autolog decorator expects a logger to exist at self.logger, and hence can only be used by MindtraceBase
    subclasses or classes that have a logger attribute.

    Args:
        log_level: The log_level passed to logger.log().
        prefix_formatter: The formatter used to log the command before the wrapped method runs. The prefix_formatter
            will be given (and must accept) three arguments, in the following order:
            - function: The function being wrapped.
            - args: The args passed into the function.
            - kwargs: The kwargs passed into the function.
        suffix_formatter: The formatter used to log the command after the wrapped method runs. The suffix_formatter
            will be given (and must accept) two arguments, in the following order:
            - function: The function being wrapped.
            - result: The result returned from the wrapped method.
        exception_formatter: The formatter used to log any errors. The exception_formatter will be given (and must
            accept) three arguments, in the following order:
            - function: The function being wrapped.
            - error: The caught Exception.
            - stack trace: The stack trace, as provided by traceback.format_exc().
        self: The instance of the class that the method is being called on. Self only needs to be passed in if the
            wrapped method does not have self as the first argument. Refer to the example below for more details.

    Example::

        from mindtrace import MindtraceBase

        class MyClass(MindtraceBase):
            def __init__(self):
                super().__init__()

            @MindtraceBase.autolog()
            def divide(self, arg1, arg2):
                self.logger.info("We are about to divide")
                result = arg1 / arg2
                self.logger.info("We have divided")
                return result

        my_instance = MyClass()
        my_instance.divide(1, 2)
        my_instance.divide(1, 0)

    The resulting log file should contain something similar to the following:

    .. code-block:: text

        MyClass - DEBUG - Calling divide with args: (1, 2) and kwargs: {}
        MyClass - INFO - We are about to divide
        MyClass - INFO - We have divided
        MyClass - DEBUG - Finished divide with result: 0.5
        MyClass - DEBUG - Calling divide with args: (1, 0) and kwargs: {}
        MyClass - INFO - We are about to divide
        MyClass - ERROR - division by zero
        Traceback (most recent call last):
        ...

    If the wrapped method does not have self as the first argument, self must be passed in as an argument to the
    autolog decorator.

    .. code-block:: python

        from fastapi import FastAPI
        from mindtrace import MindtraceBase

        class MyClass(MindtraceBase):
            def __init__():
                super().__init__()

            def create_app(self):
                app_ = FastAPI()

                @Mindtrace.autolog(self=self)  # self must be passed in as an argument as it is not captured in status()
                @app_.post("/status")
                def status():
                    return {"status": "Available"}

                return app_

    """
    prefix_formatter = ifnone(
        prefix_formatter,
        default=lambda function,
                       args,
                       kwargs: f"Calling {function.__name__} with args: {args} and kwargs: {kwargs}",
    )
    suffix_formatter = ifnone(
        suffix_formatter, default=lambda function, result: f"Finished {function.__name__} with result: {result}"
    )
    exception_formatter = ifnone(
        exception_formatter,
        default=lambda function,
                       e,
                       stack_trace: f"{function.__name__} failed to complete with the following error: {e}\n{stack_trace}",
    )

    def decorator(function):
        if self is None:

            @wraps(function)
            def wrapper(self, *args, **kwargs):
                self.logger.log(log_level, prefix_formatter(function, args, kwargs))
                try:
                    result = function(self, *args, **kwargs)
                except Exception as e:
                    self.logger.error(exception_formatter(function, e, traceback.format_exc()))
                    raise
                else:
                    self.logger.log(log_level, suffix_formatter(function, result))
                    return result

            return wrapper

        else:

            @wraps(function)
            def wrapper(*args, **kwargs):
                self.logger.log(log_level, prefix_formatter(function, args, kwargs))
                try:
                    result = function(*args, **kwargs)
                except Exception as e:
                    self.logger.error(exception_formatter(function, e, traceback.format_exc()))
                    raise
                else:
                    self.logger.log(log_level, suffix_formatter(function, result))
                    return result

            return wrapper

    return decorator


def dynamic_instantiation(module_name: str, class_name: str, **kwargs) -> object:
    """Dynamically instantiates a class from a module."""
    module = importlib.import_module(module_name)
    class_ = getattr(module, class_name)
    instance = class_(**kwargs)
    return instance


def instantiate_target(target: str, **kwargs):
    """Instantiates a target object from a string.

    The target string should be in the same format as expected from Hydra targets. I.e. 'module_name.class_name'.

    Args:
        target: A string representing a target object.

    Example::

        from mindtrace.utils import instantiate_target

        target = 'mindtrace.data.mnist.MNISTDataModule'
        mnist = instantiate_target(target)

        print(type(mnist))  # <class 'mindtrace.data.mnist.MNISTDataModule'>
    """
    module_name, class_name = target.rsplit(".", 1)
    return dynamic_instantiation(module_name, class_name, **kwargs)


def named_lambda(name: str, lambda_func: callable) -> callable:
    """Assigns a name to the given lambda function.

    This method is useful when passing lambda functions to other functions that require a name attribute. For example,
    when using the autolog decorator, the wrapped function will be logged according the function name. If the original
    function is a lambda function, it's name attribute will be set to the generic name '<lambda>'.

    Args:
        name: The name to assign to the lambda function.
        lambda_func: The lambda function to assign the name to.

    Returns:
        The lambda function with the name attribute set to the given name.

    Example::

            from mindtrace import MindtraceBase
            from mindtace.utils import named_lambda

            class HyperRunner(MindtraceBase):
                def __init__(self):
                    super().__init__()

                def run_command(self, command: callable, data: Any):  # cannot control the name of the command
                    return MindtraceBase.autolog(command(data))()

            hyper_runner = HyperRunner()
            hyper_runner.run_command(lambda x, y: x + y, data=(1, 2))  # autologs to '<lambda>'
            hyper_runner.run_command(named_lambda("add", lambda x, y: x + y), data=(1, 2))  # autologs to 'add'

    """
    lambda_func.__name__ = name
    return lambda_func


class Timeout:
    """Utility for adding a timeout to a given method.

    The given method will be run and rerun until an exception is not raised, or the timeout period is reached.

    If the method raises an exception that is in the exceptions tuple, that exception will be caught and ignored. After
    a retry_delay, the method will be run again. This process will continue until the method runs without raising an
    exception, or the timeout period is passed.

    If the timeout is reached, a TimeoutError will be raised. If the method ever raises an exception that is not in the
    exceptions tuple, the timeout process will stop and that exception will be reraised.

    Args:
        timeout: The maximum time in seconds that the method can run before a TimeoutError is raised.
        retry_delay: The time in seconds to wait between attempts to run the method.
        exceptions: A tuple of exceptions that will be caught and ignored. By default, all exceptions are caught.
        progress_bar: A boolean indicating whether to display a progress bar while waiting for the timeout.
        desc: A description to display in the progress bar.

    Returns:
        The result of the given method.

    Raises:
        TimeoutError: If the timeout is reached.
        Exception: Any raised exception not in the exceptions tuple will be reraised.

    Example— Running Timeout Manually::

        import requests
        from urllib3.util.url import parse_url, Url
        from mindtrace.services import ServerBase
        from mindtrace.utils import Timeout

        def get_server_status(url: Url):
            # The following request may fail for two categories of reasons:
            #   1. The server has not launched yet: Will raise a ConnectionError, we should retry.
            #   2. Any other reason: Will raise some other exception, we should break out and reraise it.
            # Both cases will be raised to the Timeout class. We will tell the Timeout object to ignore ConnectionError.
            response = requests.request("POST", str(url) + "status")

            if response.status_code == 200:
                return json.loads(response.content)["status"]  # Server is up and responding
            else:
                raise HTTPException(response.status_code, response.content)  # Request completed but something is wrong

        url = parse_url("http://localhost:8080/")
        timeout = Timeout(timeout=60.0, exceptions=(ConnectionRefusedError, requests.exceptions.ConnectionError))

        ServerBase.launch(url)
        status = timeout.run(get_server_status, url)  # Will wait up to 60 seconds for the server to launch.
        print(f"Server status: {status}")


    Example— Using Timeout as a Decorator::

        import requests
        from urllib3.util.url import parse_url, Url
        from mindtrace.services import ServerBase
        from mindtrace.utils import Timeout

        @Timeout(timeout=60.0, exceptions=(ConnectionRefusedError, requests.exceptions.ConnectionError))
        def get_server_status(url: Url):
            response = requests.request("POST", str(url) + "status")
            if response.status_code == 200:
                return json.loads(response.content)["status"]
            else:
                raise HTTPException(response.status_code, response.content)

        url = parse_url("http://localhost:8080/")
        ServerBase.launch(url)

        try:
            status = get_server_status(url)  # Will wait up to 60 seconds for the server to launch.
        except TimeoutError as e:
            print(f"The server did not respond within the timeout period: {e}")  # Timeout of 60 seconds reached.
        except Exception as e:  # Guaranteed not to be one of the given exceptions in the exceptions tuple.
            print(f"An unexpected error occurred: {e}")
        else:
            print(f"Server status: {status}")

    """

    def __init__(
        self,
        timeout: float = 60.0,
        retry_delay: float = 1.0,
        exceptions: tuple[Type[Exception], ...] = (Exception,),
        progress_bar: bool = False,
        desc: str | None = None,
    ):
        self.timeout = timeout
        self.retry_delay = retry_delay
        self.exceptions = exceptions
        self.progress_bar = progress_bar
        self.desc = desc

    def _wrapper(self, func, *args, **kwargs):
        _progress_bar = tqdm(total=self.timeout, desc=self.desc, leave=False) if self.progress_bar else None
        start_time = time.perf_counter()
        while True:
            if _progress_bar:
                _progress_bar.update()
            try:
                result = func(*args, **kwargs)
            except self.exceptions as e:  # ignore exception and try again after retry_delay
                if time.perf_counter() - start_time > self.timeout:
                    raise TimeoutError(f"Timeout of {self.timeout} seconds reached.") from e
                time.sleep(self.retry_delay)
            except Exception as e:  # reraise exception
                if _progress_bar:
                    _progress_bar.close()
                raise e
            else:
                if _progress_bar:
                    _progress_bar.close()
                return result

    def __call__(self, func):
        """Wrap the given function. This method allows the Timeout class to be used as a decorator."""
        return lambda *args, **kwargs: self._wrapper(func, *args, **kwargs)

    def run(self, func, *args, **kwargs):
        """Run the given function with the given args and kwargs."""
        return self._wrapper(func, *args, **kwargs)
