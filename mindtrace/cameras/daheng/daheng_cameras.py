import os
from typing import Optional, List, Tuple
import cv2
import numpy as np

try:
    import gxipy as gx
except ImportError:
    print(
        "Install gxipy to use Daheng cameras: \
	   1. Github repository: https://github.com/Mindtrace/gxipy \
	   2. uv run pip install git+https://github.com/Mindtrace/gxipy.git \
	   3. If using windows, Restart VS Code after DahengSDk installation, for environment variable updates."
    )
    raise ImportError("gxipy not found")

from mindtrace.cameras.base import BaseCamera


class DahengCamera(BaseCamera):
    def __init__(
        self,
        camera_name: str,
        camera_config: Optional[str] = "",
        img_quality_enhancement: bool = False,
        retrieve_retry_count: int = 3,
    ):
        """
        Class to manage Daheng Cameras.

                Args:
                        camera_name: user_id of Daheng camera
                        camera_config: path to camera config file
                        img_quality_enhancement: whether to apply image quality enhancement
                        retrieve_retry_count: number of times to try to retrieve image
        """
        super().__init__(camera_name=camera_name)
        self.camera_config = camera_config
        self.img_quality_enhancement = img_quality_enhancement
        self.retrieve_retry_count = retrieve_retry_count
        self.device_manager = gx.DeviceManager()
        self.initialized, self.camera, self.remote_device_feature = self.initialize()
        if self.camera is not None:
            # Set the trigger mode
            self.triggermode = "continuous" if self.camera.TriggerMode.get()[0] == 0 else "trigger"
            # Set the white balance automatically if the camera config file does not exist
            if not (os.path.exists(self.camera_config)):
                self.set_auto_wb_once("once")
            # Set the image quality enhancement
            if img_quality_enhancement:
                self.gamma_lut, self.contrast_lut, self.color_correction_param = self.img_quality_enhance_initialize()

    def initialize(self):
        """Initialize Daheng camera."""
        status = False
        camera = None
        remote_control = None
        dev_cnt, dev_info_list = self.device_manager.update_device_list()
        if dev_cnt == 0:
            raise RuntimeError("No Daheng cameras found.")

        for index, dev_info in enumerate(dev_info_list):
            if dev_info.get("user_id") == self.camera_name:
                camera = self.device_manager.open_device_by_index(index + 1)
                remote_control = camera.get_remote_device_feature_control()
                if "get_feature_control" in dir(camera.get_stream(1)):
                    stream_control = camera.get_stream(1).get_feature_control()
                elif "get_featrue_control" in dir(camera.get_stream(1)):
                    stream_control = camera.get_stream(1).get_featrue_control()
                else:
                    raise RuntimeError("Camera stream does not support feature control")

                stream_buffer_handling_mode = stream_control.get_enum_feature("StreamBufferHandlingMode")
                stream_buffer_handling_mode.set(3)  # Set buffer to be newest first
                if os.path.exists(self.camera_config):
                    camera.import_config_file(self.camera_config)
                camera.stream_on()
                status = True
                break

        return status, camera, remote_control

    @staticmethod
    def get_available_cameras() -> List[str]:
        """Get the available cameras. Returns user id of each camera"""
        device_manager = gx.DeviceManager()
        dev_cnt, dev_info_list = device_manager.update_device_list()
        return [dev_info.get("user_id") for dev_info in dev_info_list]

    def get_image_quality_enhancement(self) -> bool:
        """Get the current image quality enhancement"""
        return self.img_quality_enhancement

    def get_triggermode(self):
        """Get the current trigger mode"""
        return self.camera.TriggerMode.get()

    def get_exposure_range(self) -> List[int]:
        """Get camera exposure ranges."""
        exposure_dict = self.camera.ExposureTime.get_range()
        min_exposure, max_exposure = exposure_dict["min"], exposure_dict["max"]
        return [min_exposure, max_exposure]

    def get_width_range(self) -> List[int]:
        """Get camera width ranges."""
        width_dict = self.camera.Width.get_range()
        min_width, max_width = width_dict["min"], width_dict["max"]
        return [min_width, max_width]

    def get_height_range(self) -> List[int]:
        """Get camera height ranges."""
        height_dict = self.camera.Height.get_range()
        min_height, max_height = height_dict["min"], height_dict["max"]
        return [min_height, max_height]

    def get_wb(
        self,
    ) -> str:
        """Get the current white balance

        Returns:
            white balance value ('off' or 'on')
        """
        wb = self.camera.BalanceWhiteAuto.get()[0]
        if wb == 0:
            return "off"
        else:
            return "once"

    def get_exposure(self) -> float:
        """
        Gets the camera exposure value.

        Returns:
            exposure: float exposure value
        """
        return self.camera.ExposureTime.get()

    def set_auto_wb_once(self, value: str) -> bool:
        """Sets the white balance

        Args:
            value: white balance value to set ('off' or 'once')
        """
        status = False
        new_wb = None
        if value == "off":
            self.camera.BalanceWhiteAuto.set(0)
            new_wb = self.camera.BalanceWhiteAuto.get()[0]
        if value == "once":
            self.camera.BalanceWhiteAuto.set(2)
            new_wb = self.camera.BalanceWhiteAuto.get()[0]
        if new_wb == 2 and value == "once" or new_wb == 0 and value == "off":
            status = True
        return status

    def set_config(self, config: str):
        """Set the camera config from txt file"""
        try:
            self.camera.stream_off()
            self.camera.import_config_file(config)
            self.camera.stream_on()
        except Exception as e:
            print(f"Error setting config: {e}")
            return False
        return True

    def set_image_quality_enhancement(self, img_quality_enhancement: bool):
        """Set the image quality enhancement"""
        self.img_quality_enhancement = img_quality_enhancement
        if self.img_quality_enhancement:
            self.gamma_lut, self.contrast_lut, self.color_correction_param = self.img_quality_enhance_initialize()
        return True

    def set_triggermode(self, triggermode: str = "continuous") -> bool:
        """
        Set the trigger mode of the camera. Continuous mode returns frames at a fixed rate.
        Trigger mode returns frames only when the trigger is activated. Default is continuous mode.
        """
        if triggermode == "trigger":
            self.triggermode = "trigger"
            trigger_mode_feature = self.remote_device_feature.get_enum_feature("TriggerMode")
            trigger_mode_feature.set("On")
            trigger_source_feature = self.remote_device_feature.get_enum_feature("TriggerSource")
            trigger_source_feature.set("Software")
        else:
            self.triggermode = "continuous"
            trigger_mode_feature = self.remote_device_feature.get_enum_feature("TriggerMode")
            trigger_mode_feature.set("Off")

        set_trigger_mode = self.camera.TriggerMode.get()
        if (triggermode == "continuous" and set_trigger_mode[0] == 0) or (
            triggermode == "trigger" and set_trigger_mode[0] == 1
        ):
            return True
        else:
            return False

    def set_exposure(self, exposure_value: int) -> bool:
        """Sets the camera exposure value.

                This method goes through the following logic:
        1. First check if the exposure value is within the range.
        2. Set the value if it is within the range.
        3. Check that the correct exposure was set.
        4. Return true if set correctly, false if not.

        Args:
            exposure_value: exposure value to set

        Returns:
            bool: True if set correctly, false if not.
        """
        status = False
        exposure_dict = self.camera.ExposureTime.get_range()
        min_exposure, max_exposure = exposure_dict["min"], exposure_dict["max"]
        if min_exposure > exposure_value or max_exposure < exposure_value:
            return status
        self.camera.ExposureTime.set(float(exposure_value))
        if self.camera.ExposureTime.get() == float(exposure_value):
            status = True
        return status

    def img_quality_enhance_initialize(self):
        """Initialize the image quality enhancement used in the camera"""
        if self.camera.GammaParam.is_readable():
            gamma_value = self.camera.GammaParam.get()
            gamma_lut = gx.Utility.get_gamma_lut(gamma_value)
        else:
            gamma_lut = None
        if self.camera.ContrastParam.is_readable():
            contrast_value = self.camera.ContrastParam.get()
            contrast_lut = gx.Utility.get_contrast_lut(contrast_value)
        else:
            contrast_lut = None
            color_correction_param = self.camera.ColorCorrectionParam.get()

        return gamma_lut, contrast_lut, color_correction_param

    def close(self):
        """Close the camera and release resources"""
        if self.camera is not None:
            self.camera.stream_off()
            self.camera.close_device()

    def capture(self) -> Tuple[bool, np.ndarray]:
        """
        Capture an image from the Daheng camera.

                This method goes through the following logic:
            1. Check if camera is initialized
            2. Retrieve image. If image is incomplete, try again until retrieve_retry_count.
            3. If image is still not retrieved, return None
            4. Convert the image to RGB format, apply image improvements if necessary
            5. Convert the image to BGR format
            6. Return status and image

        Returns:
            (status: bool, image: np.ndarray)
        """
        if self.camera is None:
            raise RuntimeError("Camera not initialized. Please initialize the camera first.")
        status = False
        for i in range(self.retrieve_retry_count):
            if self.triggermode != "continuous":
                trigger_software_command_feature = self.remote_device_feature.get_command_feature("TriggerSoftware")
                trigger_software_command_feature.send_command()
            raw_image = self.camera.data_stream[0].get_image()
            if raw_image is not None:
                if raw_image.get_status() != gx.GxFrameStatusList.INCOMPLETE:
                    status = True
                    break

        if not status:
            return status, None
        rgb_image = raw_image.convert("RGB")
        if self.img_quality_enhancement:
            rgb_image.image_improvement(self.color_correction_param, self.contrast_lut, self.gamma_lut)

        image = cv2.cvtColor(rgb_image.get_numpy_array(), cv2.COLOR_RGB2BGR)

        return status, image

    def check_connection(self):
        """
        Check if Daheng camera is connected

        Returns:
            bool: True if connected, False if not
        """
        status, img = self.capture()
        if status and img.shape[0] > 0 and img.shape[1] > 0:
            return True
        else:
            return False

    def import_config(self, config_path: str):
        """Import the camera config from a txt file"""
        if not os.path.exists(config_path):
            return False
        try:
            self.camera.stream_off()
            self.camera.import_config_file(config_path)
            self.camera.stream_on()
        except Exception as e:
            print(f"Error importing config: {e}")
            return False
        return True

    def export_config(self, config_path: str):
        """Export the camera config to a txt file"""
        try:
            self.camera.stream_off()
            self.camera.export_config_file(config_path)
            self.camera.stream_on()
        except Exception as e:
            print(f"Error exporting config: {e}")
            return False
        return True

    def __del__(self):
        """Close the camera and release resources when the object is deleted"""
        self.close()


if __name__ == "__main__":
    camera_list = DahengCamera.get_available_cameras()
    print("Available cameras:", camera_list)
    if len(camera_list) > 0:
        camera = DahengCamera(camera_name=camera_list[0])
        print(camera.get_exposure())
        camera.set_exposure(1000)
        print(camera.get_exposure())
    else:
        print("No cameras found")
