"""Module for processing a single user profile (capture, stitch)."""

import logging
import os
from pathlib import Path
import time
import pyautogui
import random
from typing import Tuple, List, Optional
from rich.console import Console # Import Console
from datetime import datetime # Import datetime

# --- Import project modules ---
from tinder_bot.window import find_iphone_window 
from tinder_bot.capture import delete_screenshots # Import delete_screenshots
from tinder_bot.scroll import get_hardcoded_window # Keep this import here
# Import the new capture and stitch function
from tinder_bot.capture_and_stitch import capture_and_stitch_profile


# --- Helper Function to Process a Single Profile ---
def process_single_profile(
    env: str, 
    num_scrolls: int, 
    logger: logging.Logger, 
    console: Console,
    keep_screenshots: bool,
    debug: bool # Add debug flag parameter
) -> Tuple[Optional[str], Optional[Tuple[int, int, int, int]]]:
    """
    Finds the profile window, then calls capture_and_stitch_profile to get the stitched image.
    Handles deletion of original screenshots if requested.
    Returns the path to the stitched image and the bounding box, or None if an error occurs.
    """
    stitched_path: Optional[str] = None
    screenshot_paths: List[str] = []
    bbox: Optional[Tuple[int, int, int, int]] = None
    
    try:
        # Step 1: Find the iPhone window
        if debug:
            console.print("\n[bold]Step 1:[/bold] Finding iPhone window...")
        if env in ["PRO", "AIR", "MONITOR"]:
            bbox = get_hardcoded_window()
            if debug:
                console.print(f"Using hardcoded {env} dimensions for iPhone window")
        else:
            bbox = find_iphone_window()
            
        if not bbox:
            console.print("[bold red]ERROR:[/bold red] Could not find iPhone window.")
            return None, None # Indicate failure
        
        if debug:
            console.print(f"Found iPhone window at ({bbox[0]}, {bbox[1]}) with size {bbox[2]}x{bbox[3]}")
        
        # Step 2, 3, 4 & Stitching: Call the dedicated function, passing debug flag
        stitched_path, screenshot_paths = capture_and_stitch_profile(
            bbox=bbox, 
            env=env, 
            num_scrolls=num_scrolls, 
            logger=logger, 
            console=console,
            debug=debug # Pass the flag
        )
        
        if not stitched_path:
             # Error occurred during capture/stitch, paths might still exist for cleanup
             logger.error("Failed to capture and stitch profile image.")
             # Decide if we should still attempt cleanup
             if not keep_screenshots and screenshot_paths:
                 console.print("[yellow]Attempting cleanup of original screenshots after error...[/yellow]")
                 delete_screenshots(screenshot_paths)
             return None, bbox # Return None for path, but bbox might be useful

        # Handle deletion of originals if successfully stitched and not keeping
        if not keep_screenshots and screenshot_paths:
            if debug:
                console.print("\nDeleting original screenshots...")
            deleted_count = delete_screenshots(screenshot_paths)
            if debug:
                console.print(f"Deleted {deleted_count} original screenshots.")
            
        # Return stitched path and bbox
        return stitched_path, bbox

    except Exception as e:
        # Catch any other unexpected error during window finding or coordination
        logger.error("Error during profile processing coordination", exc_info=True)
        console.print(f"[bold red]ERROR:[/bold red] Error coordinating profile processing: {e}")
        # Attempt cleanup if paths exist
        if not keep_screenshots and screenshot_paths:
            console.print("[yellow]Attempting cleanup of original screenshots after error...[/yellow]")
            delete_screenshots(screenshot_paths)
        return None, bbox # Return None path, maybe valid bbox 