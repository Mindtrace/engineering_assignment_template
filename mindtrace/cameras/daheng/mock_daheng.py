import os
import time
import numpy as np
from typing import List
from mindtrace.cameras.base import BaseCamera


class MockDeviceManager:
    def __init__(self, num_cameras: int = 25):
        """Mock class to simulate Daheng Camera Manager"""
        self.num_cameras = num_cameras

    def get_device_list(self):
        """Mock method to get the list of Daheng cameras"""
        return [f"mock_cam_{i}" for i in range(self.num_cameras)]

    def get_device_info(self, device_id: str):
        """Mock method to get the information of a Daheng camera"""
        return {
            "user_id": device_id,
            "device_id": device_id,
            "device_name": f"mock_cam_{device_id}",
            "device_type": "Mock Daheng",
            "device_status": "connected",
        }

    def update_device_list(self):
        """Mock method to update the list of Daheng cameras"""
        return [], [self.get_device_info(f"mock_cam_{i}") for i in range(self.num_cameras)]


class MockDahengCamera(BaseCamera):
    def __init__(
        self,
        camera_name: str,
        camera_config: str = None,
        img_quality_enhancement: bool = False,
        retrieve_retry_count: int = 3,
        trigger_mode: str = "continuous",
        exposure_time: int = 1000,
        wb_mode: str = "off",
        width: int = 640,
        height: int = 480,
        lower_exposure_limit: int = 100,
        upper_exposure_limit: int = 1000000,
    ):
        """Mock class to simulate Daheng Cameras.

        Args:
            camera_name: user_id of Daheng camera
            camera_config: path to camera config file
            img_quality_enhancement: whether to apply image quality enhancement
            retrieve_retry_count: number of times to try to retrieve image
        """
        super().__init__(camera_name=camera_name)
        # Store initialization parameters
        self.camera_config = camera_config
        self.img_quality_enhancement = img_quality_enhancement
        self.retrieve_retry_count = retrieve_retry_count
        self.device_manager = MockDeviceManager()
        self.initialized = False
        self.camera = None
        self.remote_device_feature = None
        self.initialized, self.camera, self.remote_device_feature = self.initialize()

        # Mock camera state
        self.triggermode = trigger_mode
        self.exposure_time = exposure_time
        self._wb_mode = wb_mode
        self.width = width
        self.height = height
        self.lower_exposure_limit = lower_exposure_limit
        self.upper_exposure_limit = upper_exposure_limit
        self._is_connected = True

    @staticmethod
    def get_available_cameras() -> List[str]:
        """Get the available cameras. Returns user id of each camera"""
        device_manager = MockDeviceManager()
        dev_cnt, dev_info_list = device_manager.update_device_list()
        return [dev_info.get("user_id") for dev_info in dev_info_list]

    def initialize(self):
        """Mock initialization always succeeds"""
        self.initialized = True
        return True, None, None

    def set_config(self, config: str):
        """Mock config setter"""
        return True

    def get_image_quality_enhancement(self):
        """Mock image quality enhancement getter"""
        return self.img_quality_enhancement

    def set_image_quality_enhancement(self, img_quality_enhancement: bool):
        """Mock image quality enhancement setter"""
        self.img_quality_enhancement = img_quality_enhancement
        return True

    def set_triggermode(self, triggermode: str):
        """Mock trigger mode setter"""
        if triggermode in ["continuous", "trigger"]:
            self.triggermode = triggermode
            return True
        return False

    def get_triggermode(self):
        """Mock trigger mode getter"""
        return [0] if self.triggermode == "continuous" else [1]

    def get_exposure_range(self):
        """Mock exposure range"""
        return [self.lower_exposure_limit, self.upper_exposure_limit]

    def get_width_range(self):
        """Mock width range"""
        return [0, self.width]

    def get_height_range(self):
        """Mock height range"""
        return [0, self.height]

    def get_wb(self):
        """Mock white balance getter"""
        return self._wb_mode

    def set_auto_wb_once(self, value: str):
        """Mock white balance setter"""
        if value in ["off", "once"]:
            return True
        return False

    def set_exposure(self, exposure_value: int):
        """Mock exposure setter"""
        if self.lower_exposure_limit <= exposure_value <= self.upper_exposure_limit:
            self.exposure_time = float(exposure_value)
            return True
        return False

    def get_exposure(self):
        """Mock exposure getter"""
        return self.exposure_time

    def close(self):
        """Mock close"""
        self._is_connected = False

    def capture(self):
        """Return a dummy image with realistic delay

        This method simulates a realistic camera capture by:
        1. Checking connection status
        2. Adding a realistic delay (400ms)
        3. Generating a dummy image

        Returns:
            (status: bool, image: np.ndarray)
        """
        if not self._is_connected:
            return False, None

        # Simulate capture delay (blocking operation)
        time.sleep(0.4)

        # Create a dummy color image (self.height, self.width, 3) with random noise
        dummy_image = np.random.randint(0, 255, (self.height, self.width, 3), dtype=np.uint8)
        return True, dummy_image

    def check_connection(self):
        """Mock connection check"""
        return self._is_connected

    def import_config(self, config_path: str):
        """Mock config import"""
        if os.path.exists(config_path):
            return True
        return False

    def export_config(self, config_path: str):
        """Mock config export"""
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            f.write(f"width: {self.width}\nheight: {self.height}\n")
        return True

    def __del__(self):
        self.close()


if __name__ == "__main__":
    camera_list = MockDahengCamera.get_available_cameras()
    print("Available cameras:", camera_list)
    if len(camera_list) > 0:
        camera = MockDahengCamera(camera_name=camera_list[0])
        print(camera.get_exposure())
        camera.set_exposure(1000)
        print(camera.get_exposure())
        camera.close()
    else:
        print("No cameras found")
