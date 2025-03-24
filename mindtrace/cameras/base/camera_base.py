from abc import abstractmethod
import uuid
from typing import Any

def ifnone(val: Any, default: Any):
    """Return the given value if it is not None, else return the default."""
    return val if val is not None else default

class BaseCamera:
    def __init__(self, camera_name: str | None = None):
        """
        Base class for all cameras.
        """
        super().__init__()
        self.camera_name = ifnone(camera_name, str(uuid.uuid4()))
        self.camera = None
        self.device_manager = None

    @abstractmethod
    def initialize(self):
        return NotImplementedError

    @abstractmethod
    def set_parameter(self, param: str, value: any):
        return NotImplementedError

    @abstractmethod
    def get_parameter(self, param: str) -> any:
        return NotImplementedError

    @abstractmethod
    def capture_image(self) -> any:
        return NotImplementedError

    @abstractmethod
    def save_image(self, image: any, file_path: str):
        return NotImplementedError
