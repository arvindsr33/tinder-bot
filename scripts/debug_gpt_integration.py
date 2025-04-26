#!/usr/bin/env python
"""
Debug script to test GPT-4o integration with the captured screenshots.
This script will:
1. Find a stitched image from the screenshots/stitched directory
2. Send it to GPT-4o
3. Get generated openers
4. Print the results
"""

import os
import sys
import time
from pathlib import Path
import glob

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.tinder_bot.gpt import generate_opener

# Directory where stitched screenshots are stored
STITCHED_DIR = Path("./screenshots/stitched")

def find_latest_stitched_image():
    """
    Find the most recent stitched image.
    
    Returns:
        Path to the most recent stitched image or None if none found
    """
    # Get all PNG files in the stitched directory
    all_stitched = sorted(glob.glob(str(STITCHED_DIR / "profile_stitched_*.png")), 
                         key=os.path.getmtime, 
                         reverse=True)
    
    if not all_stitched:
        print("No stitched images found in", STITCHED_DIR)
        return None
    
    print(f"Found stitched image: {os.path.basename(all_stitched[0])}")
    return all_stitched[0]

def main():
    print("Testing GPT-4o integration with stitched screenshots...")
    
    # Check if API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        print("Please set it in the .env file or directly in your environment.")
        sys.exit(1)
    
    # Find the latest stitched image
    stitched_path = find_latest_stitched_image()
    if not stitched_path:
        print("No stitched images found. Run debug_scroll_and_capture.py first.")
        sys.exit(1)
    
    print("\nSending stitched image to GPT-4o for analysis...")
    
    # Generate opener based on the stitched image
    try:
        opener = generate_opener(stitched_path)
        
        print("\n===== GENERATED OPENER =====")
        print(opener)
        print("===========================")
        
    except Exception as e:
        print(f"Error during opener generation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\nGPT-4o integration test complete!")

if __name__ == "__main__":
    main()