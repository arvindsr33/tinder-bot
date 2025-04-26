"""Tests for window detection module."""

import pytest
from unittest.mock import patch, MagicMock, call
import numpy as np
import cv2
from PIL import Image
import os
from tinder_bot.window import find_iphone_window, save_detected_window


class MockWindow:
    """Mock window for testing."""
    
    def __init__(self, title, left, top, width, height):
        self.title = title
        self.left = left
        self.top = top
        self.width = width
        self.height = height


# Remove this test since getAllWindows is not available
# def test_find_iphone_window_with_window_api():
#     """Test finding iPhone window using window API."""
#     ...


def test_save_detected_window():
    """Test saving the detected window with 10% left-side expansion for manual verification."""
    # Create a mock screenshot of size 1920x1080
    mock_screenshot = Image.new('RGB', (1920, 1080), color='black')
    
    # Create a mock bbox in the middle of the screen
    x, y, width, height = 700, 200, 400, 800
    bbox = (x, y, width, height)
    
    # Calculate expected crop parameters with 10% expansion on left side
    expected_extra_width = int(width * 0.10)
    expected_left = max(0, x - expected_extra_width)  # Should be 690
    expected_right = x + width  # Should be 1140
    expected_crop_args = (expected_left, y, expected_right, y + height)
    
    # Create a temporary directory for testing
    test_dir = "./test_screenshots"
    
    # Patch the SCREENSHOT_DIR to use our test directory
    with patch('os.getenv', return_value=test_dir):
        with patch('pathlib.Path.mkdir'):  # Mock directory creation
            # Mock the crop method to check its arguments
            with patch.object(mock_screenshot, 'crop', return_value=mock_screenshot) as mock_crop:
                with patch.object(mock_screenshot, 'save'):  # Mock save operation
                    # Call the function
                    filepath = save_detected_window(mock_screenshot, bbox)
                    
                    # Check that the crop was called with the expected arguments
                    mock_crop.assert_called_once()
                    crop_args = mock_crop.call_args[0][0]
                    assert crop_args == expected_crop_args
                    
                    # Check that the filepath is correct
                    assert filepath.startswith(test_dir)
                    assert "iphone_window_" in filepath
                    assert filepath.endswith(".png")


def test_find_iphone_window_with_border_detection():
    """Test finding iPhone window using white border detection."""
    # Create a mock screenshot with iPhone proportions
    mock_screenshot = Image.new('RGB', (1920, 1080), color='black')
    
    # Define iPhone dimensions
    iphone_width = 400
    iphone_height = int(iphone_width * 19.5 / 9)
    iphone_x = (1920 - iphone_width) // 2
    iphone_y = (1080 - iphone_height) // 2
    
    # Convert to numpy array for drawing
    mock_np = np.array(mock_screenshot)
    
    # Draw white borders around iPhone screen (as seen in the screenshot)
    border_thickness = 5
    
    # Top border
    mock_np[iphone_y:iphone_y+border_thickness, iphone_x:iphone_x+iphone_width] = [255, 255, 255]
    # Bottom border
    mock_np[iphone_y+iphone_height-border_thickness:iphone_y+iphone_height, iphone_x:iphone_x+iphone_width] = [255, 255, 255]
    # Left border
    mock_np[iphone_y:iphone_y+iphone_height, iphone_x:iphone_x+border_thickness] = [255, 255, 255]
    # Right border
    mock_np[iphone_y:iphone_y+iphone_height, iphone_x+iphone_width-border_thickness:iphone_x+iphone_width] = [255, 255, 255]
    
    # Create mock grayscale and threshold images
    mock_gray = np.zeros((1080, 1920), dtype=np.uint8)
    mock_gray[iphone_y:iphone_y+iphone_height, iphone_x:iphone_x+iphone_width] = 255
    
    mock_thresh = np.zeros((1080, 1920), dtype=np.uint8)
    mock_thresh[iphone_y:iphone_y+iphone_height, iphone_x:iphone_x+iphone_width] = 255
    
    # Create a mock contour representing the iPhone outline
    mock_contour = np.array([
        [[iphone_x, iphone_y]], 
        [[iphone_x+iphone_width, iphone_y]], 
        [[iphone_x+iphone_width, iphone_y+iphone_height]], 
        [[iphone_x, iphone_y+iphone_height]]
    ])
    
    # Mock functions for first detection approach
    with patch('pyautogui.screenshot', return_value=Image.fromarray(mock_np)):
        with patch('cv2.cvtColor', side_effect=[np.array(mock_np), mock_gray]):
            with patch('cv2.threshold', side_effect=[(None, mock_thresh), (None, mock_thresh)]):
                with patch('cv2.findContours', side_effect=[([mock_contour], None), ([], None)]):
                    with patch('cv2.arcLength', return_value=2*(iphone_width + iphone_height)):
                        with patch('cv2.approxPolyDP', return_value=np.array([
                            [[iphone_x, iphone_y]],
                            [[iphone_x+iphone_width, iphone_y]],
                            [[iphone_x+iphone_width, iphone_y+iphone_height]],
                            [[iphone_x, iphone_y+iphone_height]]
                        ])):
                            with patch('cv2.boundingRect', return_value=(iphone_x, iphone_y, iphone_width, iphone_height)):
                                with patch('numpy.mean', return_value=250):  # High value to simulate white border
                                    with patch('tinder_bot.window.save_detected_window'):
                                        with patch('cv2.imwrite'):  # Mock saving debug image
                                            # Call the function
                                            result = find_iphone_window()
                                            
                                            # Check that result is a tuple with 4 elements (x, y, width, height)
                                            assert isinstance(result, tuple)
                                            assert len(result) == 4
                                            
                                            # We should get coordinates matching our mock iPhone
                                            x, y, w, h = result
                                            assert x == iphone_x
                                            assert y == iphone_y
                                            assert w == iphone_width
                                            assert h == iphone_height


def test_find_iphone_window_alternative_detection():
    """Test finding iPhone window using the alternative detection method."""
    # Create a mock screenshot
    mock_screenshot = Image.new('RGB', (1920, 1080), color='black')
    
    # Define iPhone dimensions
    iphone_width = 400
    iphone_height = int(iphone_width * 19.5 / 9)
    iphone_x = (1920 - iphone_width) // 2
    iphone_y = (1080 - iphone_height) // 2
    
    # Mock numpy arrays
    mock_np = np.zeros((1080, 1920, 3), dtype=np.uint8)
    mock_gray = np.zeros((1080, 1920), dtype=np.uint8)
    mock_thresh1 = np.zeros((1080, 1920), dtype=np.uint8)
    mock_thresh2 = np.zeros((1080, 1920), dtype=np.uint8)
    
    # Create a mock contour that will be used for the second detection attempt
    mock_contour2 = np.array([
        [[iphone_x, iphone_y]], 
        [[iphone_x+iphone_width, iphone_y]], 
        [[iphone_x+iphone_width, iphone_y+iphone_height]], 
        [[iphone_x, iphone_y+iphone_height]]
    ])
    
    # Mock functions 
    with patch('pyautogui.screenshot', return_value=mock_screenshot):
        with patch('cv2.cvtColor', side_effect=[mock_np, mock_gray]):
            with patch('cv2.threshold', side_effect=[(None, mock_thresh1), (None, mock_thresh2)]):
                # First detection fails (empty contours)
                # Second detection succeeds
                with patch('cv2.findContours', side_effect=[([], None), ([mock_contour2], None)]):
                    with patch('cv2.contourArea', return_value=iphone_width*iphone_height):
                        with patch('cv2.boundingRect', return_value=(iphone_x, iphone_y, iphone_width, iphone_height)):
                            with patch('tinder_bot.window.save_detected_window'):
                                with patch('cv2.imwrite'):  # Mock saving debug image
                                    # Call the function
                                    result = find_iphone_window()
                                    
                                    # Check that result is a tuple with 4 elements (x, y, width, height)
                                    assert isinstance(result, tuple)
                                    assert len(result) == 4
                                    
                                    # We should get coordinates matching our mock iPhone
                                    x, y, w, h = result
                                    assert x == iphone_x
                                    assert y == iphone_y
                                    assert w == iphone_width
                                    assert h == iphone_height


def test_find_iphone_window_fallback():
    """Test fallback to estimated region when detection fails."""
    # Mock screenshot size
    mock_size = (1920, 1080)
    mock_screenshot = MagicMock(size=mock_size)
    
    # Create mock arrays
    mock_np = np.zeros((1080, 1920, 3), dtype=np.uint8)
    mock_gray = np.zeros((1080, 1920), dtype=np.uint8)
    mock_thresh1 = np.zeros((1080, 1920), dtype=np.uint8)
    mock_thresh2 = np.zeros((1080, 1920), dtype=np.uint8)
    
    # Mock all detection methods to fail
    with patch('pyautogui.screenshot', return_value=mock_screenshot):
        with patch('cv2.cvtColor', side_effect=[mock_np, mock_gray]):
            with patch('cv2.threshold', side_effect=[(None, mock_thresh1), (None, mock_thresh2)]):
                with patch('cv2.findContours', side_effect=[([], None), ([], None)]):  # Both detection attempts fail
                    with patch('tinder_bot.window.save_detected_window'):
                        with patch('cv2.imwrite'):  # Mock saving debug image
                            # Call the function
                            result = find_iphone_window()
                            
                            # We expect an estimated region in the center of the screen
                            x, y, width, height = result
                            
                            # Check that width is about 1/4 of screen width
                            assert width == mock_size[0] // 4
                            
                            # Check that height maintains iPhone aspect ratio
                            assert abs(width / height - 9 / 19.5) < 0.1
                            
                            # Check that it's centered
                            assert x == (mock_size[0] - width) // 2
                            assert y == (mock_size[1] - height) // 2 