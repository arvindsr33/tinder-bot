#!/usr/bin/env python
"""
Debug script to test iPhone window detection, scrolling, screenshot capture, and image stitching.
This script will:
1. Use hardcoded values for the iPhone window
2. Position the cursor at the center
3. Perform exactly 5 scrolls to capture a full profile
4. Take 6 high-quality screenshots in total (initial + after each scroll)
5. Stitch the 6 screenshots into a single image in a 3x2 grid
"""

import os
import sys
import time
import pyautogui
from pathlib import Path
from PIL import Image
import numpy as np
import glob
import argparse

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Parse command line arguments
parser = argparse.ArgumentParser(description='Test iPhone window detection and scrolling')
parser.add_argument('--env', choices=['MONITOR', 'MAC'], default='MONITOR',
                    help='Specify environment (MONITOR or MAC)')
args = parser.parse_args()

# Set debug mode and environment
os.environ["DEBUG_SCROLL"] = "True"
os.environ["ENVIRONMENT"] = args.env
print(f"Using environment: {args.env}")

from src.tinder_bot.window import find_iphone_window
from src.tinder_bot.scroll import scroll_profile, get_hardcoded_window, perform_stepped_scroll
from src.tinder_bot.image_utils import stitch_images
from src.tinder_bot.capture import take_region_screenshot, save_screenshot

# Create screenshots directory if it doesn't exist
SCREENSHOTS_DIR = Path("./screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Create stitched directory if it doesn't exist
STITCHED_DIR = SCREENSHOTS_DIR / "stitched"
STITCHED_DIR.mkdir(exist_ok=True)

# Screenshot quality settings
SCREENSHOT_FORMAT = "png"  # Use lossless PNG format
SCREENSHOT_DPI = 600  # High DPI for better quality

def take_high_quality_screenshot(bbox, index):
    """
    Take a high-quality screenshot of the iPhone window area.
    
    Args:
        bbox: (x, y, width, height) of the iPhone window
        index: Screenshot index number for filename (1-6)
    
    Returns:
        Path to the saved screenshot
    """
    x, y, width, height = bbox
    
    # Create the filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = SCREENSHOTS_DIR / f"profile_screenshot_{index}_{timestamp}.{SCREENSHOT_FORMAT}"
    
    print(f"Taking high-quality screenshot #{index}/6...")
    
    # Use PyAutoGUI for initial capture
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
    
    print(f"High-quality screenshot saved to: {filename}")
    return filename

def scroll_and_capture(bbox):
    """
    Scroll through a profile while taking high-quality screenshots at each step.
    
    Args:
        bbox: (x, y, width, height) of the iPhone window
        
    Returns:
        List of paths to the 6 screenshots taken
    """
    from src.tinder_bot.scroll import (
        FIRST_SCROLL_AMOUNT, SUBSEQUENT_SCROLL_AMOUNT, SCROLL_DELAY, 
        NUM_SCROLLS, UP_SCROLL_AMOUNT, STEPS_PER_SCROLL, STEP_DELAY
    )
    
    screenshot_paths = []
    
    # Move to center and get coordinates
    x, y, width, height = bbox
    center_x = x + width // 2
    center_y = y + height // 2
    
    print(f"iPhone window: ({x}, {y}) to ({x+width}, {y+height})")
    print(f"Center point: ({center_x}, {center_y})")
    print(f"Window dimensions: {width}x{height} pixels")
    
    # Move to center and click to ensure focus
    pyautogui.moveTo(center_x, center_y, duration=0.5)
    pyautogui.click()
    time.sleep(1.0)
    
    print("\n===== SCROLLING AND CAPTURING HIGH-QUALITY SCREENSHOTS =====")
    print(f"First scroll: {FIRST_SCROLL_AMOUNT} pixels in {STEPS_PER_SCROLL} steps")
    print(f"Subsequent scrolls: {SUBSEQUENT_SCROLL_AMOUNT} pixels in {STEPS_PER_SCROLL} steps")
    print(f"Total screenshots: 6 (initial + 5 scrolls)")
    print(f"Delay between scrolls: {SCROLL_DELAY} seconds")
    print(f"Screenshot format: {SCREENSHOT_FORMAT.upper()} with {SCREENSHOT_DPI} DPI")
    
    # Take initial high-quality screenshot (before any scrolling)
    screenshot_path = take_high_quality_screenshot(bbox, 1)
    screenshot_paths.append(screenshot_path)
    
    # Perform scrolls and take screenshots
    for i in range(5):  # Total of 5 scrolls
        # Determine the scroll amount (first scroll is different)
        scroll_amount = FIRST_SCROLL_AMOUNT if i == 0 else SUBSEQUENT_SCROLL_AMOUNT
        screenshot_number = i + 2  # Screenshots 2-6
        
        print(f"\nPerforming scroll {i+1}/5 ({scroll_amount} pixels)...")
        
        # Click before each scroll to ensure window focus is maintained
        pyautogui.click(center_x, center_y)
        time.sleep(0.1)
        
        # Use stepped scrolling
        perform_stepped_scroll(scroll_amount)
        
        # Wait for content to load
        time.sleep(SCROLL_DELAY)
        
        # Take the high-quality screenshot
        screenshot_path = take_high_quality_screenshot(bbox, screenshot_number)
        screenshot_paths.append(screenshot_path)
    
    print("\nFinished scrolling and capturing, pausing to ensure content is loaded...")
    time.sleep(2.0)
    
    # Scroll back to top for next profile
    print("\nScrolling back to top of profile...")
    # Calculate how many up-scrolls needed based on total distance scrolled
    total_scroll_distance = abs(FIRST_SCROLL_AMOUNT) + abs(SUBSEQUENT_SCROLL_AMOUNT) * (NUM_SCROLLS - 1)
    scrolls_needed = total_scroll_distance // abs(UP_SCROLL_AMOUNT) + 1
    
    for i in range(scrolls_needed):
        pyautogui.click(center_x, center_y)
        time.sleep(0.1)
        print(f"Scroll up {i+1}/{scrolls_needed}: {UP_SCROLL_AMOUNT} pixels in {STEPS_PER_SCROLL} steps")
        perform_stepped_scroll(UP_SCROLL_AMOUNT)
        time.sleep(0.5)
    
    print("\nProfile scrolling and high-quality screenshot capture complete!")
    print(f"All screenshots saved to: {SCREENSHOTS_DIR}")
    
    return screenshot_paths

def find_latest_screenshots():
    """
    Find the 6 most recent screenshots in the screenshots directory.
    
    Returns:
        List of paths to the 6 screenshots in order
    """
    # Get all PNG files in the screenshots directory
    all_screenshots = sorted(glob.glob(str(SCREENSHOTS_DIR / "profile_screenshot_*.png")), 
                            key=os.path.getmtime, 
                            reverse=True)
    
    # Organize by screenshot number (1-6)
    organized_screenshots = {}
    for path in all_screenshots:
        filename = os.path.basename(path)
        parts = filename.split('_')
        if len(parts) >= 2 and parts[1].isdigit():
            num = int(parts[1])
            if 1 <= num <= 6:
                # Get or create list for this number
                if num not in organized_screenshots:
                    organized_screenshots[num] = []
                organized_screenshots[num].append(path)
    
    # Get the most recent screenshot for each position
    result = []
    for num in range(1, 7):
        if num in organized_screenshots and organized_screenshots[num]:
            result.append(organized_screenshots[num][0])
    
    return sorted(result, key=lambda x: int(os.path.basename(x).split('_')[1]))

def main():
    print(f"Starting iPhone window detection, scrolling, screenshot capture, and stitching test in {args.env} environment...")
    
    # Print environment info
    print(f"Environment: {os.getenv('ENVIRONMENT')}")
    screen_width, screen_height = pyautogui.size()
    print(f"Actual screen resolution: {screen_width}x{screen_height}")
    
    # Get hardcoded window dimensions
    try:
        bbox = get_hardcoded_window()
        print(f"\nUsing hardcoded {args.env} iPhone window dimensions:")
        x, y, width, height = bbox
        print(f"Position: Top-left ({x}, {y}), Bottom-right ({x+width}, {y+height})")
        print(f"Size: {width}x{height}")
        
        # Verify cursor can move to the iPhone center
        center_x = x + width // 2
        center_y = y + height // 2
        print(f"iPhone center: ({center_x}, {center_y})")
        
        input("\nPress Enter to move cursor to the iPhone center for verification...")
        pyautogui.moveTo(center_x, center_y, duration=1.0)
        time.sleep(1.0)
        
        input("\nPress Enter to begin scrolling and capturing high-quality screenshots...")
        
        # Run the scroll and capture function
        screenshot_paths = scroll_and_capture(bbox)
        
        print(f"\nCapturing complete! Took {len(screenshot_paths)} screenshots.")
        
        # Stitch the screenshots together
        print("\n===== STITCHING SCREENSHOTS =====")
        if len(screenshot_paths) == 6:
            try:
                # Import the stitch_images function
                from src.tinder_bot.image_utils import stitch_images
                
                # Stitch the screenshots
                print("Stitching screenshots into a single image...")
                stitched_path = stitch_images(screenshot_paths, delete_originals=False)
                
                print(f"Stitched image saved to: {stitched_path}")
                print("\nAll operations completed successfully!")
            except Exception as e:
                print(f"Error stitching screenshots: {e}")
        else:
            print(f"Expected 6 screenshots, but captured {len(screenshot_paths)}. Skipping stitching.")
            
    except NotImplementedError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 