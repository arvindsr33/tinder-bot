"""Tests for the GPT integration module."""

import pytest
import os
from unittest.mock import patch, MagicMock
from PIL import Image
import io
import tempfile

from tinder_bot.gpt import (
    generate_opener, encode_image, optimize_image,
    FALLBACK_MESSAGE
)


@pytest.fixture
def mock_image_file():
    """Create a temporary image file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp:
        # Create a small test image
        img = Image.new('RGB', (100, 100), color='white')
        img.save(temp.name, format='PNG')
        yield temp.name
    # Clean up
    os.unlink(temp.name)


@pytest.fixture
def mock_large_image_file():
    """Create a temporary large image file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp:
        # Create a larger test image
        img = Image.new('RGB', (1000, 1000), color='white')
        img.save(temp.name, format='PNG')
        
        # Mock the file size to make it appear larger
        with patch('os.path.getsize', return_value=6 * 1024 * 1024):  # 6MB
            yield temp.name
    # Clean up
    os.unlink(temp.name)


def test_encode_image(mock_image_file):
    """Test that encode_image properly converts an image to base64."""
    # Encode the test image
    base64_string = encode_image(mock_image_file)
    
    # Check that it's a non-empty string
    assert isinstance(base64_string, str)
    assert len(base64_string) > 0
    
    # Check that it's valid base64
    import base64
    try:
        decoded = base64.b64decode(base64_string)
        assert len(decoded) > 0
    except Exception:
        pytest.fail("Generated string is not valid base64")


def test_optimize_image(mock_large_image_file):
    """Test that optimize_image reduces the size of large images."""
    # Optimize the test image
    optimized_path = optimize_image(mock_large_image_file, max_size_mb=3.0)
    
    # Check that a new file was created
    assert optimized_path != mock_large_image_file
    assert os.path.exists(optimized_path)
    
    # Clean up
    os.unlink(optimized_path)


def test_generate_opener_with_api_key():
    """Test that generate_opener calls the OpenAI API with correct parameters."""
    # Mock environment and OpenAI client
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), \
         patch('openai.OpenAI') as mock_openai:
        
        # Setup mock response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a test opener"
        mock_client.chat.completions.create.return_value = mock_response
        
        # Mock image processing
        with patch('tinder_bot.gpt.encode_image', return_value="test-base64"), \
             patch('tinder_bot.gpt.optimize_image', side_effect=lambda x: x):
            
            # Call the function with mock image paths
            result = generate_opener(["test1.png", "test2.png"])
            
            # Check that the result matches the mock response
            assert result == "This is a test opener"
            
            # Verify that the OpenAI client was created with the API key
            mock_openai.assert_called_once_with(api_key="test-key")
            
            # Verify that the chat completion was called with the right parameters
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args[1]
            assert "model" in call_args
            assert "messages" in call_args
            assert "max_tokens" in call_args
            assert "temperature" in call_args


def test_generate_opener_without_api_key():
    """Test that generate_opener returns a fallback message when API key is missing."""
    # Ensure OPENAI_API_KEY is not set
    with patch.dict(os.environ, {}, clear=True):
        result = generate_opener(["test.png"])
        assert result == FALLBACK_MESSAGE


def test_generate_opener_handles_api_error():
    """Test that generate_opener handles API errors gracefully."""
    # Mock environment and OpenAI client
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), \
         patch('openai.OpenAI') as mock_openai:
        
        # Setup mock client to raise an exception
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API error")
        
        # Mock image processing
        with patch('tinder_bot.gpt.encode_image', return_value="test-base64"), \
             patch('tinder_bot.gpt.optimize_image', side_effect=lambda x: x):
            
            # Call the function
            result = generate_opener(["test.png"])
            
            # Check that the fallback message is returned
            assert result == FALLBACK_MESSAGE 