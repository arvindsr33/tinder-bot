"""Tests for message input module."""

import pytest
from unittest.mock import patch, MagicMock, call
from tinder_bot.message import send_opener


def test_paste_message(mock_window_bbox):
    """Test that send_opener correctly pastes message."""
    test_opener = "Hey! I noticed you like hiking. What's your favorite trail?"
    
    # Mock pyautogui functions
    with patch('pyautogui.click') as mock_click, \
         patch('pyautogui.typewrite') as mock_typewrite, \
         patch('time.sleep') as mock_sleep:
        
        # Call the function
        send_opener(test_opener, mock_window_bbox)
        
        # Check that pyautogui.click was called at least once
        assert mock_click.call_count >= 1
        
        # Check that pyautogui.typewrite was called with the opener
        mock_typewrite.assert_called_with(test_opener)
        
        # Check that time.sleep was called at least once
        assert mock_sleep.call_count >= 1


def test_send_opener_handles_empty_message():
    """Test that send_opener handles empty messages gracefully."""
    bbox = (100, 100, 400, 800)
    
    # Mock pyautogui functions
    with patch('pyautogui.click') as mock_click, \
         patch('pyautogui.typewrite') as mock_typewrite:
        
        # Call with empty string
        send_opener("", bbox)
        
        # Check that typewrite was not called
        mock_typewrite.assert_not_called()


def test_send_opener_handles_long_message():
    """Test that send_opener handles very long messages."""
    bbox = (100, 100, 400, 800)
    long_opener = "A" * 300  # Create a 300-character string
    
    # Mock pyautogui functions
    with patch('pyautogui.click'), \
         patch('pyautogui.typewrite') as mock_typewrite:
        
        # Call the function
        send_opener(long_opener, bbox)
        
        # Check that typewrite was called with a truncated message
        args, _ = mock_typewrite.call_args
        assert len(args[0]) <= 200 