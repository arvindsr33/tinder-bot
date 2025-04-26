#!/usr/bin/env python
"""
Debug script to test iPhone window detection and scrolling.
This script will:
1. Use hardcoded values for the iPhone window
2. Position the cursor at the center
3. Perform exactly 5 scrolls to capture a full profile
"""

import os
import sys
import time
import pyautogui

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set debug mode and environment
os.environ["DEBUG_SCROLL"] = "True"
os.environ["ENVIRONMENT"] = "MONITOR"  # Set to use hardcoded MONITOR values

from src.tinder_bot.window import find_iphone_window
from src.tinder_bot.scroll import scroll_profile, get_hardcoded_window

def main():
    print("Starting iPhone window detection and scrolling test with hardcoded values...")
    print("This script demonstrates the full scrolling pattern for a Hinge profile.")
    
    # Print environment info
    print(f"Environment: {os.getenv('ENVIRONMENT', 'MONITOR')}")
    screen_width, screen_height = pyautogui.size()
    print(f"Actual screen resolution: {screen_width}x{screen_height}")
    
    # Get hardcoded window dimensions
    try:
        x, y, width, height = get_hardcoded_window()
        print(f"\nUsing hardcoded iPhone window dimensions:")
        print(f"Position: Top-left ({x}, {y}), Bottom-right ({x+width}, {y+height})")
        print(f"Size: {width}x{height}")
        
        # Calculate center
        center_x = x + width // 2
        center_y = y + height // 2
        print(f"Center point: ({center_x}, {center_y})")
        
        input("Press Enter to move cursor to the iPhone center...")
        
        # Move cursor to iPhone center
        pyautogui.moveTo(center_x, center_y, duration=0.5)
        pyautogui.click()
        
        # Show all four corners of the iPhone for better visualization
        corners = [
            (x, y, "top-left"),
            (x + width, y, "top-right"),
            (x + width, y + height, "bottom-right"),
            (x, y + height, "bottom-left")
        ]
        
        print("\nShowing iPhone boundaries...")
        for corner_x, corner_y, corner_name in corners:
            print(f"Moving to {corner_name} corner: ({corner_x}, {corner_y})")
            pyautogui.moveTo(corner_x, corner_y, duration=0.5)
            time.sleep(0.3)
        
        # Return to center
        pyautogui.moveTo(center_x, center_y, duration=0.5)
        
        input("\nPress Enter to begin full profile scrolling test...")
        
        print("\n===== FULL PROFILE SCROLLING TEST =====")
        print("First scroll: -660 pixels")
        print("Subsequent scrolls: -720 pixels")
        print("Total screenshots: 6 (initial + 5 scrolls)")
        print("Delay between scrolls: 2.0 seconds")
        
        # Run the full scroll_profile function
        scroll_profile((x, y, width, height))
        
    except NotImplementedError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()