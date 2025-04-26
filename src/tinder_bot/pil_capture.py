"""Screenshot capture and processing module using PIL."""

from typing import List, Tuple, Optional
from PIL import Image
import pyautogui
import os
import logging
from datetime import datetime
import math
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

# iPhone aspect ratio (width:height)
IPHONE_ASPECT_RATIO = 11 / 19.5

# Directory for saving screenshots
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "./screenshots")

# Screenshot quality settings
SCREENSHOT_FORMAT = "png"  # Use lossless PNG format
SCREENSHOT_DPI = 300  # High DPI for better quality


def take_screenshot() -> Image.Image:
    """
    Take a full screenshot of the screen with high quality.
    
    Returns:
        PIL.Image: Screenshot as PIL Image
    """
    logger.debug("Taking full screenshot")
    screenshot = pyautogui.screenshot()
    logger.debug(f"Took screenshot with dimensions: {screenshot.size}")
    return screenshot


def take_region_screenshot(bbox: Tuple[int, int, int, int], high_dpi: bool = True) -> Image.Image:
    """
    Take a high-quality screenshot of a specific region using the full screen 
    capture + crop method for maximum quality.
    
    Args:
        bbox: (x, y, width, height) of the region to capture
        high_dpi: Whether to apply high DPI settings
        
    Returns:
        PIL.Image: High-quality cropped screenshot
    """
    x, y, width, height = bbox
    
    # Take full screenshot
    full_screenshot = take_screenshot()
    
    # Crop to region
    region_image = full_screenshot.crop((x, y, x + width, y + height))
    
    # For high DPI images, we keep the original resolution but set DPI metadata
    if high_dpi:
        # This doesn't change the pixel dimensions but sets the DPI metadata
        # which affects how the image is displayed/printed
        region_image.info['dpi'] = (300, 300)
    
    logger.debug(f"Cropped screenshot to region {bbox} with dimensions: {region_image.size}")
    return region_image


def save_screenshot(image: Image.Image, filename: str, dpi: int = 300) -> str:
    """
    Save a screenshot with high quality settings.
    
    Args:
        image: Image to save
        filename: Filename to save as
        dpi: DPI value for the saved image
        
    Returns:
        str: Path to the saved file
    """
    # Create screenshots directory if it doesn't exist
    Path(SCREENSHOT_DIR).mkdir(exist_ok=True)
    
    # Full path
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    
    # Save with high quality settings
    image.save(
        filepath, 
        format=SCREENSHOT_FORMAT.upper(),
        dpi=(dpi, dpi),
        quality=100  # Maximum quality (only applies to JPEG)
    )
    
    logger.debug(f"Saved screenshot to {filepath}")
    return filepath


def crop_phone_screen(
    screenshot: Image.Image, bbox: Tuple[int, int, int, int]
) -> Image.Image:
    """
    Crop a screenshot to the iPhone screen area with the correct aspect ratio.
    
    Args:
        screenshot: Full screenshot as PIL Image
        bbox: Bounding box of iPhone window (x, y, width, height)
        
    Returns:
        PIL.Image: Cropped image with iPhone aspect ratio (9:19.5)
    """
    x, y, width, height = bbox
    
    # First crop to the window boundaries
    window_crop = screenshot.crop((x, y, x + width, y + height))
    
    # Now adjust to iPhone aspect ratio if needed
    current_ratio = width / height
    target_ratio = IPHONE_ASPECT_RATIO
    
    if math.isclose(current_ratio, target_ratio, rel_tol=0.05):
        logger.debug("Window already has correct aspect ratio, no further cropping needed")
        return window_crop
    
    logger.debug(f"Adjusting aspect ratio from {current_ratio:.4f} to {target_ratio:.4f}")
    
    # Calculate the new dimensions to maintain the correct aspect ratio
    if current_ratio > target_ratio:
        # Window is too wide, crop width
        new_width = int(height * target_ratio)
        left_margin = (width - new_width) // 2
        phone_crop = window_crop.crop((left_margin, 0, left_margin + new_width, height))
    else:
        # Window is too tall, crop height
        new_height = int(width / target_ratio)
        top_margin = (height - new_height) // 2
        phone_crop = window_crop.crop((0, top_margin, width, top_margin + new_height))
    
    logger.info(f"Cropped screenshot to iPhone aspect ratio: {phone_crop.size}")
    return phone_crop


def split_profile_blocks(
    cropped_screen: Image.Image, num_blocks: int = 6
) -> List[Image.Image]:
    """
    Split a cropped iPhone screen into sections for separate processing.
    
    Args:
        cropped_screen: Cropped iPhone screen as PIL Image
        num_blocks: Number of sections to split into (default 6)
        
    Returns:
        List of PIL.Image objects representing profile sections
    """
    width, height = cropped_screen.size
    block_height = height // num_blocks
    
    blocks = []
    for i in range(num_blocks):
        # Calculate the top and bottom coordinates for this block
        top = i * block_height
        # For the last block, include any remaining pixels
        bottom = height if i == num_blocks - 1 else (i + 1) * block_height
        
        # Crop to get this block
        block = cropped_screen.crop((0, top, width, bottom))
        blocks.append(block)
        
        logger.debug(f"Created block {i+1}/{num_blocks}: {block.size}")
    
    logger.info(f"Split profile into {num_blocks} blocks")
    return blocks


def save_screenshots(blocks: List[Image.Image], profile_name: str) -> List[str]:
    """
    Save screenshot blocks to disk with high quality.
    
    Args:
        blocks: List of image blocks to save
        profile_name: Name of the profile for filename
        
    Returns:
        List of filenames where images were saved
    """
    # Create screenshots directory if it doesn't exist
    Path(SCREENSHOT_DIR).mkdir(exist_ok=True)
    
    # Generate timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save each block
    filenames = []
    for i, block in enumerate(blocks):
        # Generate filename with profile name, block number and timestamp
        filename = f"{profile_name}_block{i+1}_{timestamp}.{SCREENSHOT_FORMAT}"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        
        # Save with high quality settings
        block.save(
            filepath, 
            format=SCREENSHOT_FORMAT.upper(),
            dpi=(SCREENSHOT_DPI, SCREENSHOT_DPI),
            quality=100  # Maximum quality (only applies to JPEG)
        )
        
        logger.debug(f"Saved block {i+1} to {filepath}")
        filenames.append(filepath)
    
    logger.info(f"Saved {len(blocks)} screenshot blocks for profile '{profile_name}'")
    return filenames 