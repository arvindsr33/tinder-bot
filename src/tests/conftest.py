"""Pytest fixtures for Tinder Bot tests."""

import pytest
from PIL import Image
import io
import os
from typing import Tuple


@pytest.fixture
def mock_window_bbox() -> Tuple[int, int, int, int]:
    """Return a mock window bounding box."""
    return (100, 100, 400, 800)


@pytest.fixture
def mock_screenshot() -> Image.Image:
    """Create a mock screenshot for testing."""
    # Create a blank image with desktop dimensions
    return Image.new('RGB', (1920, 1080), color='white')


@pytest.fixture
def mock_phone_screenshot() -> Image.Image:
    """Create a mock iPhone screenshot with 9:19.5 aspect ratio."""
    # iPhone aspect ratio is approximately 9:19.5
    width = 300
    height = int(width * 19.5 / 9)
    return Image.new('RGB', (width, height), color='white') 