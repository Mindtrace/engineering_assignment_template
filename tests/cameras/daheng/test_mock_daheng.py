import pytest
import numpy as np
from mindtrace.cameras.daheng.mock_daheng import MockDahengCamera


@pytest.fixture
def mock_camera():
    """Fixture to create a mock camera instance."""
    return MockDahengCamera(camera_name="mock_cam_0")


def test_get_available_cameras():
    """Test the retrieval of available cameras."""
    cameras = MockDahengCamera.get_available_cameras()
    assert isinstance(cameras, list), "Cameras is not a list"
    assert len(cameras) > 0, "No cameras found"
    assert all(isinstance(cam, str) for cam in cameras), "Cameras are not strings"


def test_initialize(mock_camera):
    """Test the initialization of the camera."""
    assert mock_camera.initialized is True, "Camera is not initialized"


def test_set_and_get_image_quality_enhancement(mock_camera):
    """Test setting and getting image quality enhancement."""
    assert mock_camera.get_image_quality_enhancement() is False, "Image quality enhancement is not False"
    mock_camera.set_image_quality_enhancement(True)
    assert mock_camera.get_image_quality_enhancement() is True, "Image quality enhancement is not True"


def test_set_and_get_triggermode(mock_camera):
    """Test setting and getting trigger mode."""
    initial_mode = mock_camera.get_triggermode()[0]
    assert mock_camera.set_triggermode("trigger") is True, "Failed to set trigger mode to trigger"
    assert mock_camera.get_triggermode()[0] == 1, "Trigger mode is not 1"
    assert mock_camera.set_triggermode("continuous") is True, "Failed to set trigger mode to continuous"
    assert mock_camera.get_triggermode()[0] == 0, "Trigger mode is not 0"
    # Reset to initial mode
    mock_camera.set_triggermode("trigger" if initial_mode == 1 else "continuous")


def test_get_exposure_range(mock_camera):
    """Test getting the exposure range."""
    exposure_range = mock_camera.get_exposure_range()
    assert isinstance(exposure_range, list), "Exposure range is not a list"
    assert len(exposure_range) == 2, "Exposure range does not have 2 elements"
    assert exposure_range[0] < exposure_range[1], "Exposure range is not in ascending order"


def test_get_width_range(mock_camera):
    """Test getting the width range."""
    width_range = mock_camera.get_width_range()
    assert isinstance(width_range, list), "Width range is not a list"
    assert len(width_range) == 2, "Width range does not have 2 elements"
    assert width_range[0] < width_range[1], "Width range is not in ascending order"


def test_get_height_range(mock_camera):
    """Test getting the height range."""
    height_range = mock_camera.get_height_range()
    assert isinstance(height_range, list), "Height range is not a list"
    assert len(height_range) == 2, "Height range does not have 2 elements"
    assert height_range[0] < height_range[1], "Height range is not in ascending order"


def test_set_and_get_wb(mock_camera):
    """Test setting and getting white balance."""
    assert mock_camera.get_wb() == "off", "White balance is not off"
    assert mock_camera.set_auto_wb_once("once") is True, "Failed to set white balance to once"
    assert mock_camera.set_auto_wb_once("invalid") is False, "Failed to set white balance to invalid"


def test_set_and_get_exposure(mock_camera):
    """Test setting and getting exposure."""
    initial_exposure = mock_camera.get_exposure()
    exposure_range = mock_camera.get_exposure_range()
    new_exposure = (exposure_range[0] + exposure_range[1]) // 2
    assert mock_camera.set_exposure(new_exposure) is True, "Failed to set exposure to new_exposure"
    assert mock_camera.get_exposure() == new_exposure, "Exposure is not new_exposure"
    # Reset to initial exposure
    assert mock_camera.set_exposure(initial_exposure) is True, "Failed to reset exposure to initial_exposure"
    assert mock_camera.get_exposure() == initial_exposure, "Exposure is not initial_exposure"


def test_capture(mock_camera):
    """Test capturing an image."""
    status, image = mock_camera.capture()
    assert status is True, "Failed to capture image"
    assert isinstance(image, np.ndarray), "Image is not a numpy array"
    assert image.shape[0] > 0 and image.shape[1] > 0, "Image shape is invalid"


def test_check_connection(mock_camera):
    """Test checking the connection status."""
    assert mock_camera.check_connection() is True, "Failed to check connection"


def test_get_wb(mock_camera):
    """Test getting the white balance."""
    wb = mock_camera.get_wb()
    assert wb in ["off", "once"], "White balance is not off or once"


def test_set_auto_wb_once(mock_camera):
    """Test setting the white balance to 'once'."""
    assert mock_camera.set_auto_wb_once("once") is True, "Failed to set white balance to once"
    assert mock_camera.set_auto_wb_once("off") is True, "Failed to set white balance to off"
    assert mock_camera.get_wb() == "off", "White balance is not off"


def test_export_config(tmp_path, mock_camera):
    """Test exporting the camera configuration."""
    config_path = tmp_path / "camera_config.txt"
    assert mock_camera.export_config(str(config_path)) is True, "Failed to export camera configuration"
    assert config_path.exists(), "Camera configuration file does not exist"


def test_import_config(tmp_path, mock_camera):
    """Test importing camera configuration."""
    config_path = tmp_path / "camera_config.txt"
    # Ensure the config file exists by exporting first
    assert mock_camera.export_config(str(config_path)) is True, "Failed to export camera configuration"
    assert config_path.exists(), "Camera configuration file does not exist"
    assert mock_camera.import_config(str(config_path)) is True, "Failed to import camera configuration"
