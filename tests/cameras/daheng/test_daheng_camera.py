import pytest
import numpy as np
from mindtrace.cameras.daheng.daheng_cameras import DahengCamera


@pytest.fixture
def camera():
    """Fixture to create a DahengCamera instance."""
    camera_list = DahengCamera.get_available_cameras()
    if not camera_list:
        pytest.skip("No Daheng cameras found.")
    camera = DahengCamera(camera_name=camera_list[0])
    yield camera
    camera.close()


def test_get_available_cameras(camera):
    """Test the retrieval of available cameras."""
    cameras = camera.get_available_cameras()
    assert isinstance(cameras, list), "Cameras is not a list"
    assert len(cameras) >= 0, "No cameras found"
    assert all(isinstance(cam, str) for cam in cameras), "Cameras are not strings"


def test_initialize(camera):
    """Test the initialization of the camera."""
    assert camera.initialized is True, "Camera is not initialized"


def test_set_and_get_image_quality_enhancement(camera):
    """Test setting and getting image quality enhancement."""
    camera.set_image_quality_enhancement(True)
    assert camera.get_image_quality_enhancement() is True, "Image quality enhancement is not True"
    camera.set_image_quality_enhancement(False)
    assert camera.get_image_quality_enhancement() is False, "Image quality enhancement is not False"


def test_set_and_get_triggermode(camera):
    """Test setting and getting trigger mode."""
    initial_mode = camera.get_triggermode()[0]
    assert camera.set_triggermode("trigger") is True, "Failed to set trigger mode to trigger"
    assert camera.get_triggermode()[0] == 1, "Trigger mode is not 1"
    assert camera.set_triggermode("continuous") is True, "Failed to set trigger mode to continuous"
    assert camera.get_triggermode()[0] == 0, "Trigger mode is not 0"
    # Reset to initial mode
    camera.set_triggermode("trigger" if initial_mode == 1 else "continuous")


def test_get_exposure_range(camera):
    """Test getting the exposure range."""
    exposure_range = camera.get_exposure_range()
    assert isinstance(exposure_range, list), "Exposure range is not a list"
    assert len(exposure_range) == 2, "Exposure range does not have 2 elements"
    assert exposure_range[0] < exposure_range[1], "Exposure range is not in ascending order"


def test_get_width_range(camera):
    """Test getting the width range."""
    width_range = camera.get_width_range()
    assert isinstance(width_range, list), "Width range is not a list"
    assert len(width_range) == 2, "Width range does not have 2 elements"
    assert width_range[0] < width_range[1], "Width range is not in ascending order"


def test_get_height_range(camera):
    """Test getting the height range."""
    height_range = camera.get_height_range()
    assert isinstance(height_range, list), "Height range is not a list"
    assert len(height_range) == 2, "Height range does not have 2 elements"
    assert height_range[0] < height_range[1], "Height range is not in ascending order"


def test_set_and_get_wb(camera):
    """Test setting and getting white balance."""
    assert camera.set_auto_wb_once("once") is True, "Failed to set white balance to once"
    assert camera.get_wb() == "once", "White balance is not once"
    assert camera.set_auto_wb_once("off") is True, "Failed to set white balance to off"
    assert camera.get_wb() == "off", "White balance is not off"
    assert camera.set_auto_wb_once("invalid") is False, "Failed to set white balance to invalid"


def test_set_and_get_exposure(camera):
    """Test setting and getting exposure."""
    initial_exposure = camera.get_exposure()
    exposure_range = camera.get_exposure_range()
    new_exposure = (exposure_range[0] + exposure_range[1]) // 2
    assert camera.set_exposure(new_exposure) is True, "Failed to set exposure to new_exposure"
    assert camera.get_exposure() == new_exposure, "Exposure is not new_exposure"
    # Reset to initial exposure
    assert camera.set_exposure(initial_exposure) is True, "Failed to reset exposure to initial_exposure"
    assert camera.get_exposure() == initial_exposure, "Exposure is not initial_exposure"


def test_capture(camera):
    """Test capturing an image."""
    status, image = camera.capture()
    assert status is True, "Failed to capture image"
    assert isinstance(image, np.ndarray), "Image is not a numpy array"
    assert image.shape[0] > 0 and image.shape[1] > 0, "Image shape is invalid"


def test_check_connection(camera):
    """Test checking the connection status."""
    assert camera.check_connection() is True, "Failed to check connection"


def test_get_wb(camera):
    """Test getting the white balance."""
    wb = camera.get_wb()
    assert wb in ["off", "once"], "White balance is not off or once"


def test_set_auto_wb_once(camera):
    """Test setting the white balance to 'once'."""
    assert camera.set_auto_wb_once("once") is True, "Failed to set white balance to once"
    assert camera.set_auto_wb_once("off") is True, "Failed to set white balance to off"
    assert camera.get_wb() == "off", "White balance is not off"


def test_export_config(camera, tmp_path):
    """Test exporting camera configuration."""
    config_path = tmp_path / "camera_config.txt"
    assert camera.export_config(str(config_path)) is True, "Failed to export camera configuration"
    assert config_path.exists(), "Camera configuration file does not exist"


def test_import_config(camera, tmp_path):
    """Test importing camera configuration."""
    config_path = tmp_path / "camera_config.txt"
    # Ensure the config file exists by exporting first
    assert camera.export_config(str(config_path)) is True, "Failed to export camera configuration"
    assert config_path.exists(), "Camera configuration file does not exist"
    assert camera.import_config(str(config_path)) is True, "Failed to import camera configuration"
