# Daheng Camera Interface

The following instructions are to setup and use Daheng cameras for camera capture.
## Installation

Requires sudo access to install Daheng SDK.
```bash
cd mt-rix
uv sync
uv run python -m mindtrace.scripts.camera_setup
```

## Usage

### 1. Listing Available Cameras
To view the entire list of available cameras, use the following command:
```python
from mindtrace.cameras.daheng.daheng_cameras import DahengCamera
camera_list = DahengCamera.get_available_cameras()
print('Available cameras:', camera_list)
```

### 2. Initializing a Camera
Cameras are initialized by passing their user id as the camera name, and an optional camera config txt file that contains camera settings.
The cameras will be instantiated in their last saved state.
To initialize a camera, use the following command:
```python
camera = DahengCamera(camera_name='camera-user-id', '/path/to/camera_config.txt')
```
The camera class can be initialized with the following additional arguments:
- `img_quality_enhancement`: Whether to apply image quality enhancement.
- `retrieve_retry_count`: Number of times to retry to retrieve image.

### 3. Setting Trigger Mode
The cameras support two modes of capture:
- Continuous mode: The camera captures images continuously.
- Trigger mode: The camera captures images only when the trigger is activated.

To set the trigger mode of the camera, use the following command:
```python
camera.set_triggermode('trigger')
camera.set_triggermode('continuous')
```

### 4. Capturing Images
Images are captured by calling the `capture` method. If an image is not retrieved in the first attempt, the camera will retry to retrieve the image using the `retrieve_retry_count` argument. If the image is not retrieved, the method will return `False` and `None`, else it will return `True` and the np BGR image.
To capture images, use the following command:
```python
status, image = camera.capture()
```

### 5. Closing the Camera
Cameras are closed automatically when the camera object is destroyed.

### 6. Exporting Camera Settings
To export the camera settings to a txt file, use the following command:
```python
camera.export_config('/path/to/camera_config.txt')
```

### 7. Importing Camera Settings
The camera can be instantiated with its settings during initialization by passing the path to the config file. Alternatively, to import the camera settings, use the following command:
```python
camera.import_config('/path/to/camera_config.txt')
```

### 8. Additional Features
The camera class has various additional features which can be used to control the camera. A few of them are listed below:
- `get_exposure_range`: Get the supported exposure range of the camera.
- `get_exposure`: Get the current exposure value of the camera.
- `set_exposure`: Set the exposure value of the camera.
- `get_auto_wb_once`: Get the current white balance mode of the camera.
- `set_auto_wb_once`: Set the white balance mode of the camera.
- `check_connection`: Check if the camera is connected by capturing an image.
- `get_width_range`: Get the supported width range of the camera.
- `get_height_range`: Get the supported height range of the camera.
- `get_wb`: Get the current white balance of the camera.
- `set_wb`: Set the white balance of the camera.

## Mock Camera
A mock camera is also available to test the camera interface without the need to connect to a physical camera. All methods are replicated as is, and can be accessed in the same way as the real camera. Below is a sample pipeline usage to capture an image from a mock camera. Calling the capture method will return a randomly generated image. All cameras will be initialized with a user id in format `mock_cam_<index>`.
```python
from mindtrace.cameras.daheng.mock_daheng import MockDahengCamera
camera_list = MockDahengCamera.get_available_cameras()
print('Available cameras:', camera_list)
if len(camera_list) > 0:
    camera = MockDahengCamera(camera_name=camera_list[0])
    status, image = camera.capture()
    print(f"Capture status: {status}")
    print(f"Image shape: {image.shape if image is not None else None}")
    camera.close()
else:
    print("No cameras found")
```

## Running Tests
Tests can be run for both the actual and the mock camera.
1. Run the tests for the mock camera
```bash
uv run python -m pytest tests/cameras/daheng/test_mock_daheng.py -v
```
2. Run the tests for the actual camera
```bash	
uv run python -m pytest tests/cameras/daheng/test_daheng_camera.py -v
```