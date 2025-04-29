"""Screenshot capture module for Tinder Bot using direct region capture."""

from typing import Tuple, Optional
import pyautogui
import numpy as np
from PIL import Image
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Directory for saving screenshots
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "./screenshots")

# Screenshot quality settings
SCREENSHOT_FORMAT = "png"  # Use lossless PNG format
SCREENSHOT_DPI = 600  # High DPI for better quality

def take_high_quality_screenshot(
    bbox: Tuple[int, int, int, int], 
    index: int, 
    timestamp: str,
    output_dir: Optional[str] = None
) -> str:
    """
    Take a high-quality screenshot of the iPhone window area using direct region capture.
    
    Args:
        bbox: (x, y, width, height) of the iPhone window
        index: Screenshot index number for filename (1-6)
        timestamp: Timestamp string for the filename
        output_dir: Optional custom output directory (defaults to SCREENSHOT_DIR)
    
    Returns:
        Path to the saved screenshot
    """
    x, y, width, height = bbox
    
    # Use custom output directory if provided, otherwise use default
    screenshots_dir = Path(output_dir if output_dir else SCREENSHOT_DIR)
    screenshots_dir.mkdir(exist_ok=True)
    
    # Create the filename
    filename = screenshots_dir / f"profile_screenshot_{index}_{timestamp}.{SCREENSHOT_FORMAT}"
    
    logger.info(f"Taking high-quality screenshot #{index} at position ({x}, {y}) with size {width}x{height}")
    
    # Use PyAutoGUI for direct region capture
    screenshot = pyautogui.screenshot(region=(x, y, width, height))
    
    # Convert to numpy array for processing
    img_array = np.array(screenshot)
    
    # Convert back to PIL Image with higher quality settings
    high_quality_img = Image.fromarray(img_array)
    
    # Save with high DPI and quality settings
    high_quality_img.save(
        filename, 
        format=SCREENSHOT_FORMAT,
        dpi=(SCREENSHOT_DPI, SCREENSHOT_DPI),
        quality=100  # Maximum quality (only applies to JPEG)
    )
    
    logger.info(f"Saved high-quality screenshot #{index} to {filename}")
    return str(filename)

def delete_screenshots(screenshot_paths):
    """
    Delete screenshot files after they've been stitched together.
    
    Args:
        screenshot_paths: List of paths to screenshot files to delete
        
    Returns:
        int: Number of files deleted
    """
    count = 0
    for path in screenshot_paths:
        try:
            os.remove(path)
            logger.info(f"Deleted screenshot: {path}")
            count += 1
        except Exception as e:
            logger.warning(f"Failed to delete {path}: {e}")
    
    logger.info(f"Deleted {count} screenshots after stitching")
    return count 