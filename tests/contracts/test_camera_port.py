"""
Contract tests for CameraPort adapters.
"""

from typing import Any
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from packages.core.ports.camera import CameraPort
from packages.adapters.desktop.camera import OpenCVCameraAdapter
from apps.familyrobot.wiring import MockCameraAdapter


@pytest.fixture
def mock_video_capture():
    with patch("cv2.VideoCapture") as mock_cap_cls:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cap_cls.return_value = mock_cap
        yield mock_cap_cls, mock_cap


@pytest.mark.contract
@pytest.mark.asyncio
async def test_mock_camera_adapter_contract():
    """Verify MockCameraAdapter satisfies the CameraPort contract."""
    adapter: CameraPort = MockCameraAdapter()
    
    # Contract asserts
    assert isinstance(adapter, CameraPort)
    
    await adapter.open()
    frame = await adapter.capture()
    assert frame is None  # Mock returns None
    await adapter.close()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_opencv_camera_adapter_contract(mock_video_capture):
    """Verify OpenCVCameraAdapter satisfies the CameraPort contract."""
    mock_cap_cls, mock_cap = mock_video_capture
    adapter: CameraPort = OpenCVCameraAdapter(device_index=0)
    
    # Contract asserts
    assert isinstance(adapter, CameraPort)
    
    await adapter.open()
    mock_cap_cls.assert_called_once_with(0)
    mock_cap.isOpened.assert_called_once()
    
    frame = await adapter.capture()
    assert frame is not None
    assert isinstance(frame, np.ndarray)
    assert frame.shape == (480, 640, 3)
    mock_cap.read.assert_called_once()
    
    await adapter.close()
    mock_cap.release.assert_called_once()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_opencv_camera_adapter_open_failure():
    """Verify OpenCVCameraAdapter raises RuntimeError if camera fails to open."""
    with patch("cv2.VideoCapture") as mock_cap_cls:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_cls.return_value = mock_cap
        
        adapter = OpenCVCameraAdapter(device_index=1)
        with pytest.raises(RuntimeError, match="Failed to open camera index 1"):
            await adapter.open()
