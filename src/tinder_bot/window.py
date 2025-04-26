"""Window detection module for identifying iPhone mirroring windows."""

from typing import Tuple, Optional
import pyautogui
import logging
import cv2
import numpy as np
from PIL import Image
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# iPhone app visual characteristics
HINGE_APP_TOP_COLOR = (255, 255, 255)  # White background at the top of Hinge profile
HINGE_PROFILE_HEADER_COLOR = (60, 60, 60)  # Dark gray text for header

# Directory for saving screenshots
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "./screenshots")

# Get environment setting
ENVIRONMENT = os.getenv("ENVIRONMENT", "MONITOR")

def save_detected_window(screenshot: Image.Image, bbox: Tuple[int, int, int, int]) -> str:
    """
    Save the detected iPhone window region for manual verification.
    
    Args:
        screenshot: Full screenshot as PIL Image
        bbox: Bounding box of detected iPhone window (x, y, width, height)
        
    Returns:
        str: Path to the saved image
    """
    # Create screenshots directory if it doesn't exist
    Path(SCREENSHOT_DIR).mkdir(exist_ok=True)
    
    # Generate timestamp for unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"iphone_window_{timestamp}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    
    # Crop screenshot to the detected region, making it 10% wider on the left side
    x, y, width, height = bbox
    
    # Calculate 10% of the width to expand left side
    extra_width = int(width * 0.10)
    
    # Adjust x coordinate and width, ensuring we don't go off-screen
    new_x = max(0, x - extra_width)
    new_width = width + (x - new_x)  # Add the actual amount we expanded
    
    # Crop the screenshot with the expanded region
    window_crop = screenshot.crop((new_x, y, x + width, y + height))
    
    # Save the cropped image
    window_crop.save(filepath)
    logger.info(f"Saved detected iPhone window to {filepath} (width expanded by 10% on left)")
    
    return filepath

def find_iphone_window() -> Tuple[int, int, int, int]:
    """
    Find the iPhone window on screen using visual detection or hardcoded values.
    
    Returns:
        Tuple[int, int, int, int]: (x, y, width, height) of the iPhone window or fallback region
    """
    # If the environment is set, use hardcoded values
    if ENVIRONMENT == "MONITOR" or ENVIRONMENT == "MAC":
        logger.info(f"Using hardcoded {ENVIRONMENT} dimensions for iPhone window")
        from tinder_bot.scroll import get_hardcoded_window
        bbox = get_hardcoded_window()
        
        # Take a screenshot to save the window visualization
        screenshot = pyautogui.screenshot()
        save_detected_window(screenshot, bbox)
        
        return bbox
    
    # Otherwise try visual detection
    logger.info("Searching for iPhone window using border detection...")
    
    # Take a screenshot of the entire screen
    screenshot = pyautogui.screenshot()
    screenshot_np = np.array(screenshot)
    screenshot_rgb = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
    
    # Get the screen dimensions
    screen_width, screen_height = screenshot.size
    
    # Convert to grayscale for easier processing
    gray = cv2.cvtColor(screenshot_rgb, cv2.COLOR_BGR2GRAY)
    
    # Binary threshold to isolate white borders (higher threshold to focus on the white borders)
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    
    # Find contours in the thresholded image
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    logger.debug(f"Found {len(contours)} contours in the image")
    
    # Filter contours by size, shape, and white border characteristics
    for contour in contours:
        # Get approximate polygon for this contour
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        
        # iPhone screen will have roughly 4-8 points (considering the rounded corners)
        if 4 <= len(approx) <= 8:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check if it has phone-like proportions (height > width)
            if h > w and h > 200:  # Ensure it's not too small
                # Calculate aspect ratio
                aspect_ratio = w / h
                expected_ratio = 9 / 19.5  # iPhone aspect ratio
                
                # If aspect ratio is close to iPhone's (with some flexibility)
                if 0.3 < aspect_ratio < 0.6:
                    # Additional check for iPhone characteristics
                    
                    # 1. Check for white borders
                    # Sample points along the edges to verify they're white
                    top_edge = gray[y:y+5, x:x+w]
                    bottom_edge = gray[y+h-5:y+h, x:x+w]
                    left_edge = gray[y:y+h, x:x+5]
                    right_edge = gray[y:y+h, x+w-5:x+w]
                    
                    # Calculate average color for each edge
                    top_color = np.mean(top_edge)
                    bottom_color = np.mean(bottom_edge)
                    left_color = np.mean(left_edge)
                    right_color = np.mean(right_edge)
                    
                    # If most edges are predominantly white (threshold 230)
                    edge_threshold = 230
                    white_edges_count = sum(1 for color in [top_color, bottom_color, left_color, right_color] if color > edge_threshold)
                    
                    if white_edges_count >= 3:  # At least 3 edges should be white
                        logger.info(f"Found iPhone screen with white borders at ({x}, {y}, {w}, {h})")
                        logger.debug(f"Edge colors: top={top_color:.1f}, bottom={bottom_color:.1f}, left={left_color:.1f}, right={right_color:.1f}")
                        
                        # Save the detected window for manual verification
                        bbox = (x, y, w, h)
                        save_detected_window(screenshot, bbox)
                        
                        return bbox
    
    # If detection fails, try a second approach focusing on the actual screen area
    # (which would appear as a large rectangle with content)
    logger.debug("First detection approach failed, trying alternative method...")
    
    # Use a lower threshold to detect the content area
    _, thresh2 = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours2, _ = cv2.findContours(thresh2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Sort contours by area (largest first)
    contours2 = sorted(contours2, key=cv2.contourArea, reverse=True)
    
    # Examine the top few contours
    for i, contour in enumerate(contours2[:5]):  # Only check the 5 largest
        x, y, w, h = cv2.boundingRect(contour)
        
        # Check if it has phone-like proportions
        if h > w and h > 300:  # Ensure it's not too small
            aspect_ratio = w / h
            
            if 0.3 < aspect_ratio < 0.6:
                logger.info(f"Found possible iPhone screen using alternative method at ({x}, {y}, {w}, {h})")
                
                # Save the detected window for manual verification
                bbox = (x, y, w, h)
                save_detected_window(screenshot, bbox)
                
                return bbox
    
    # If both detection methods fail, fall back to a reasonable estimate
    # Based on the screenshot, we estimate iPhone would be about 1/4 of screen width
    estimated_width = screen_width // 4
    estimated_height = int(estimated_width * 19.5 / 9)  # iPhone aspect ratio
    x = (screen_width - estimated_width) // 2  # Center horizontally
    y = (screen_height - estimated_height) // 2  # Center vertically
    
    logger.warning("No iPhone window detected, using estimated region in screen center")
    
    # Save the fallback window region for manual verification
    bbox = (x, y, estimated_width, estimated_height)
    save_detected_window(screenshot, bbox)
    
    return bbox 