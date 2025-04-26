#!/usr/bin/env python3
"""
Test script for window detection.

This script will run the window detection function and save the result
to the screenshots directory for manual verification.
"""

import os
import sys
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from tinder_bot.window import find_iphone_window

def setup_logging():
    """Set up logging for the test script."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ]
    )

def main():
    """Run the window detection test."""
    setup_logging()
    
    print("Starting window detection test...")
    print("This will take a screenshot and attempt to find an iPhone window.")
    print("The result will be saved to the './screenshots' directory.")
    
    try:
        # Run the window detection function
        bbox = find_iphone_window()
        
        print(f"Window detection complete. Bounding box: {bbox}")
        print("Check the './screenshots' directory for the saved image.")
        
    except Exception as e:
        print(f"Error during window detection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 