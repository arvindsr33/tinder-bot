"""Tests for screenshot capture module."""

import pytest
from PIL import Image
import math
import os
from unittest.mock import patch, MagicMock
from tinder_bot.capture import (
    crop_phone_screen, 
    split_profile_blocks, 
    save_screenshots,
    take_screenshot,
    IPHONE_ASPECT_RATIO
)


def test_crop_to_phone_aspect(mock_screenshot, mock_window_bbox):
    """Test that crop_phone_screen produces correct aspect ratio."""
    # Call the function
    result = crop_phone_screen(mock_screenshot, mock_window_bbox)
    
    # Check that the result is a PIL Image
    assert isinstance(result, Image.Image)
    
    # Check the aspect ratio is correct (iPhone aspect ratio is approximately 9:19.5)
    width, height = result.size
    actual_ratio = width / height
    
    # Allow a small margin of error for rounding
    assert math.isclose(actual_ratio, IPHONE_ASPECT_RATIO, rel_tol=0.05)


def test_split_profile_blocks(mock_phone_screenshot):
    """Test that split_profile_blocks returns 6 images."""
    # Call the function
    results = split_profile_blocks(mock_phone_screenshot)
    
    # Check that we get 6 images (3 photos, 3 prompts)
    assert len(results) == 6
    
    # Check that all results are PIL Images
    for img in results:
        assert isinstance(img, Image.Image)


def test_save_screenshots(mock_phone_screenshot, tmpdir):
    """Test that save_screenshots correctly saves images to disk."""
    # Setup: Create 6 mock images
    blocks = [mock_phone_screenshot] * 6
    
    # Patch the SCREENSHOT_DIR to use a temp directory
    with patch('tinder_bot.capture.SCREENSHOT_DIR', str(tmpdir)):
        # Call the function
        result_paths = save_screenshots(blocks, prefix="test")
        
        # Check that we get 6 file paths
        assert len(result_paths) == 6
        
        # Check that the files exist
        for path in result_paths:
            assert os.path.exists(path)
            
            # Check that the file is a valid image
            img = Image.open(path)
            assert isinstance(img, Image.Image)


def test_take_screenshot():
    """Test that take_screenshot returns a PIL Image."""
    # Mock pyautogui.screenshot to return a mock image
    mock_img = Image.new('RGB', (1920, 1080), color='white')
    
    with patch('pyautogui.screenshot', return_value=mock_img):
        # Call the function
        result = take_screenshot()
        
        # Check that the result is a PIL Image
        assert isinstance(result, Image.Image)
        
        # Check that the dimensions match
        assert result.size == (1920, 1080)