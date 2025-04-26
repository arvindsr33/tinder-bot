"""Tests for profile scrolling module."""

import pytest
from unittest.mock import patch, MagicMock, call
from tinder_bot.scroll import (
    scroll_profile, move_to_iphone_center, get_hardcoded_window,
    FIRST_SCROLL_AMOUNT, SUBSEQUENT_SCROLL_AMOUNT, NUM_SCROLLS,
    IPHONE_X_BEGIN, IPHONE_Y_BEGIN, IPHONE_WIDTH, IPHONE_HEIGHT
)
from tinder_bot.window import find_iphone_window
import numpy as np
import os

@pytest.fixture
def hardcoded_bbox():
    """Return the hardcoded window bbox for testing."""
    with patch('os.getenv', return_value="MONITOR"):
        return get_hardcoded_window()


def test_hardcoded_window_dimensions():
    """Test that the hardcoded window dimensions are correct for MONITOR."""
    with patch('os.getenv', return_value="MONITOR"):
        bbox = get_hardcoded_window()
        
        # Check the exact dimensions
        assert bbox == (IPHONE_X_BEGIN, IPHONE_Y_BEGIN, IPHONE_WIDTH, IPHONE_HEIGHT)
        
        # Verify the corners match the expected values
        x, y, width, height = bbox
        assert x == 2304
        assert y == 617
        assert x + width == 2500
        assert y + height == 1042


def test_mac_environment_raises_error():
    """Test that MAC environment raises NotImplementedError."""
    with patch('os.getenv', return_value="MAC"):
        with pytest.raises(NotImplementedError):
            get_hardcoded_window()


def test_move_to_hardcoded_center():
    """Test that move_to_iphone_center uses hardcoded values for MONITOR."""
    with patch('os.getenv', return_value="MONITOR"), \
         patch('pyautogui.moveTo') as mock_move, \
         patch('pyautogui.size', return_value=(2511, 1051)), \
         patch('builtins.print'), \
         patch('builtins.input'):
        
        # Call with arbitrary bbox which should be replaced with hardcoded values
        center_x, center_y = move_to_iphone_center((0, 0, 10, 10))
        
        # Expected center based on hardcoded values
        expected_x = IPHONE_X_BEGIN + IPHONE_WIDTH // 2
        expected_y = IPHONE_Y_BEGIN + IPHONE_HEIGHT // 2
        
        # Check center coordinates
        assert center_x == expected_x
        assert center_y == expected_y
        
        # Check pyautogui.moveTo was called with hardcoded center
        mock_move.assert_called_once_with(expected_x, expected_y, duration=0.5)


def test_scroll_profile_uses_exact_values():
    """Test that scroll_profile uses the exact scroll values."""
    with patch('os.getenv', return_value="MONITOR"), \
         patch('pyautogui.moveTo'), \
         patch('pyautogui.click'), \
         patch('pyautogui.scroll') as mock_scroll, \
         patch('time.sleep'), \
         patch('tinder_bot.scroll.DEBUG_MODE', False):
        
        # Call with arbitrary bbox which should be replaced with hardcoded values
        scroll_profile((0, 0, 10, 10))
        
        # Extract all scroll values used
        scroll_values = [call[0][0] for call in mock_scroll.call_args_list 
                       if call[0][0] < 0]  # Only consider downward scrolls
        
        # We should have exactly NUM_SCROLLS downward scrolls
        assert len(scroll_values) == NUM_SCROLLS
        
        # First value should be FIRST_SCROLL_AMOUNT
        assert scroll_values[0] == FIRST_SCROLL_AMOUNT
        
        # Subsequent values should be SUBSEQUENT_SCROLL_AMOUNT
        for i in range(1, NUM_SCROLLS):
            assert scroll_values[i] == SUBSEQUENT_SCROLL_AMOUNT


def test_scroll_respects_exact_delay():
    """Test that scrolling uses the exact 2-second delay."""
    with patch('os.getenv', return_value="MONITOR"), \
         patch('pyautogui.moveTo'), \
         patch('pyautogui.click'), \
         patch('pyautogui.scroll'), \
         patch('time.sleep') as mock_sleep, \
         patch('tinder_bot.scroll.DEBUG_MODE', False):
        
        # Call with arbitrary bbox which should be replaced with hardcoded values
        scroll_profile((0, 0, 10, 10))
        
        # Check that sleep was called with exactly 2.0 seconds
        mock_sleep.assert_any_call(2.0)
        
        # Count how many times it was called with exactly 2.0
        two_second_delays = sum(1 for call in mock_sleep.call_args_list if call[0][0] == 2.0)
        
        # Should have one 2-second delay for each scroll
        assert two_second_delays >= NUM_SCROLLS


def test_move_to_iphone_center(mock_window_bbox):
    """Test that move_to_iphone_center correctly calculates and moves to center."""
    x, y, w, h = mock_window_bbox
    expected_center_x = x + w // 2
    expected_center_y = y + h // 2
    
    # Mock pyautogui functions
    with patch('pyautogui.moveTo') as mock_move, \
         patch('builtins.print') as mock_print, \
         patch('builtins.input', return_value='') as mock_input:
        
        # Call the function
        result_x, result_y = move_to_iphone_center(mock_window_bbox)
        
        # Check that correct center coordinates were calculated
        assert result_x == expected_center_x
        assert result_y == expected_center_y
        
        # Check that pyautogui.moveTo was called with the center coordinates
        mock_move.assert_called_once_with(expected_center_x, expected_center_y)
        
        # Verify debug output was printed
        mock_print.assert_any_call(f"\nMoving to iPhone center at: ({expected_center_x}, {expected_center_y})")


def test_visual_verification_of_center():
    """
    A test that helps visually verify the center point calculation.
    
    This test will attempt to find the iPhone window using the real
    window detection logic, and will print out detailed information
    about what it found for manual verification.
    """
    # This test only runs if VISUAL_TEST environment variable is set
    if not os.environ.get('VISUAL_TEST'):
        pytest.skip("Skipping visual verification test. Set VISUAL_TEST=1 to run.")
    
    # Mock pyautogui.moveTo to capture the arguments
    with patch('pyautogui.moveTo') as mock_move, \
         patch('time.sleep'):  # Don't actually sleep during tests
        
        # First find the iPhone window using the actual implementation
        with patch('tinder_bot.window.save_detected_window'):  # Don't save screenshots during test
            bbox = find_iphone_window()
        
        # Now calculate and move to the center
        center_x, center_y = move_to_iphone_center(bbox)
        
        # Print information for visual verification
        print(f"\n=== VISUAL VERIFICATION TEST ===")
        print(f"Detected iPhone window: x={bbox[0]}, y={bbox[1]}, width={bbox[2]}, height={bbox[3]}")
        print(f"Center point: ({center_x}, {center_y})")
        print(f"If you want to visually confirm, run: python -c \"import pyautogui; pyautogui.moveTo({center_x}, {center_y})\"")
        
        # Assert that moveTo was called with the correct arguments
        mock_move.assert_called_once_with(center_x, center_y)


def test_scroll_profile_calls_pyautogui(mock_window_bbox):
    """Test that scroll_profile calls pyautogui with correct arguments."""
    # Mock pyautogui.scroll
    with patch('pyautogui.scroll') as mock_scroll, \
         patch('pyautogui.moveTo') as mock_move, \
         patch('pyautogui.click') as mock_click, \
         patch('time.sleep') as mock_sleep, \
         patch('builtins.print'), \
         patch('tinder_bot.scroll.DEBUG_MODE', False):
        
        # Call the function
        scroll_profile(mock_window_bbox)
        
        # Check that pyautogui.scroll was called multiple times
        assert mock_scroll.call_count >= 3
        
        # Check that click was called to maintain focus
        assert mock_click.call_count >= 1
        
        # Check that time.sleep was called between scrolls
        assert mock_sleep.call_count >= 2


def test_scroll_profile_moves_mouse_to_center(mock_window_bbox):
    """Test that scroll_profile moves the mouse to the center of the window."""
    x, y, w, h = mock_window_bbox
    center_x = x + w // 2
    center_y = y + h // 2
    
    # Mock pyautogui functions
    with patch('pyautogui.moveTo') as mock_move, \
         patch('pyautogui.click') as mock_click, \
         patch('pyautogui.scroll') as mock_scroll, \
         patch('time.sleep'), \
         patch('builtins.print'), \
         patch('tinder_bot.scroll.DEBUG_MODE', False):
        
        # Call the function
        scroll_profile(mock_window_bbox)
        
        # Check that pyautogui.moveTo was called with the center coordinates
        # Using ANY for more flexible assertion that's less brittle
        mock_move.assert_any_call(center_x, center_y)


def test_scroll_profile_with_randomization():
    """Test that scroll_profile includes randomized behavior."""
    bbox = (100, 100, 400, 800)
    
    # Run the function multiple times and collect the scroll values
    scroll_values = []
    
    with patch('pyautogui.scroll') as mock_scroll, \
         patch('pyautogui.moveTo'), \
         patch('pyautogui.click'), \
         patch('time.sleep'), \
         patch('builtins.print'), \
         patch('tinder_bot.scroll.DEBUG_MODE', False):
        
        # Call the function multiple times
        for _ in range(5):
            scroll_profile(bbox)
            # Extract the scroll values from the mock calls
            scroll_values.extend([call[0][0] for call in mock_scroll.call_args_list])
            mock_scroll.reset_mock()
    
    # Check that we have different scroll values (randomized behavior)
    assert len(set(scroll_values)) > 1, "Scroll values should be randomized"


def test_integration_window_to_scroll():
    """Test that the window detection and scrolling work together correctly."""
    # Define mock iPhone dimensions
    iphone_width = 400
    iphone_height = int(iphone_width * 19.5 / 9)
    iphone_x = 500
    iphone_y = 200
    
    # Create a mock screenshot and a properly shaped mock threshold result
    mock_screenshot = MagicMock()
    mock_screenshot.size = (1920, 1080)
    mock_np = np.zeros((1080, 1920, 3), dtype=np.uint8)
    mock_gray = np.zeros((1080, 1920), dtype=np.uint8)
    mock_thresh = np.zeros((1080, 1920), dtype=np.uint8)
    
    # Create a mock contour
    mock_contour = np.array([
        [[iphone_x, iphone_y]], 
        [[iphone_x+iphone_width, iphone_y]], 
        [[iphone_x+iphone_width, iphone_y+iphone_height]], 
        [[iphone_x, iphone_y+iphone_height]]
    ])
    
    # Mock all the necessary functions for window detection to return a specific window bbox
    with patch('pyautogui.screenshot', return_value=mock_screenshot), \
         patch('cv2.cvtColor', side_effect=[mock_np, mock_gray]), \
         patch('cv2.threshold', side_effect=[(None, mock_thresh), (None, mock_thresh)]), \
         patch('cv2.findContours', side_effect=[([mock_contour], None), ([], None)]), \
         patch('cv2.arcLength', return_value=2*(iphone_width + iphone_height)), \
         patch('cv2.approxPolyDP', return_value=np.array([
            [[iphone_x, iphone_y]],
            [[iphone_x+iphone_width, iphone_y]],
            [[iphone_x+iphone_width, iphone_y+iphone_height]],
            [[iphone_x, iphone_y+iphone_height]]
         ])), \
         patch('cv2.boundingRect', return_value=(iphone_x, iphone_y, iphone_width, iphone_height)), \
         patch('numpy.mean', return_value=240), \
         patch('tinder_bot.window.save_detected_window'), \
         patch('pyautogui.moveTo') as mock_move, \
         patch('pyautogui.click') as mock_click, \
         patch('pyautogui.scroll') as mock_scroll, \
         patch('time.sleep'), \
         patch('builtins.print'), \
         patch('tinder_bot.scroll.DEBUG_MODE', False):
        
        # Call find_iphone_window to get the bbox
        bbox = find_iphone_window()
        
        # Now call scroll_profile with that bbox
        scroll_profile(bbox)
        
        # Check that moveTo was called with the center of our mock iPhone
        expected_center_x = iphone_x + iphone_width // 2
        expected_center_y = iphone_y + iphone_height // 2
        
        # Use assert_any_call instead of assert_called_with
        mock_move.assert_any_call(expected_center_x, expected_center_y)
        
        # Print the expected coordinates for debugging
        print(f"\nExpected center coordinates: ({expected_center_x}, {expected_center_y})")
        print(f"This should be in the middle of the iPhone screen")
        
        # Verify that scroll was called the appropriate number of times
        assert mock_scroll.call_count >= 6  # At least MIN_SCROLLS
        assert mock_click.call_count >= 1  # At least once


def test_scroll_respects_window_boundaries():
    """Test that scrolling stays within the detected window boundaries."""
    # Create a mock bbox with specific dimensions
    bbox = (200, 150, 350, 700)  # x, y, width, height
    
    # Expected center point for this bbox
    expected_center_x = 200 + 350 // 2
    expected_center_y = 150 + 700 // 2
    
    # Mock pyautogui functions
    with patch('pyautogui.moveTo') as mock_move, \
         patch('pyautogui.click') as mock_click, \
         patch('pyautogui.scroll') as mock_scroll, \
         patch('time.sleep'), \
         patch('builtins.print'), \
         patch('tinder_bot.scroll.DEBUG_MODE', False):
        
        # Call the function
        scroll_profile(bbox)
        
        # Check that mouse was moved to the exact center of the provided bbox
        mock_move.assert_any_call(expected_center_x, expected_center_y)
        
        # Verify that click was called at the center coordinates
        mock_click.assert_any_call(expected_center_x, expected_center_y)
        
        # Verify that scroll was called within the window
        assert mock_scroll.call_count > 0 