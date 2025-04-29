"""Module responsible for capturing profile screenshots and stitching them."""

import logging
import os
from pathlib import Path
import time
import pyautogui
import random
from typing import Tuple, List, Optional
from rich.console import Console
from datetime import datetime

# --- Import project modules ---
from tinder_bot.capture import take_high_quality_screenshot
from tinder_bot.scroll import (
    get_safe_coordinates,
    FIRST_SCROLL_AMOUNT, SUBSEQUENT_SCROLL_AMOUNT, SCROLL_DELAY,
    UP_SCROLL_AMOUNT, STEPS_PER_SCROLL, perform_stepped_scroll, NEXT_PHOTO_POS
)
from tinder_bot.image_utils import stitch_images

def capture_and_stitch_profile(
    bbox: Tuple[int, int, int, int], 
    env: str, 
    num_scrolls: int, 
    logger: logging.Logger, 
    console: Console,
    debug: bool
) -> Tuple[Optional[str], List[str]]:
    """
    Captures screenshots for a profile (clicking or scrolling based on env) and stitches them.
    
    Args:
        bbox: The bounding box of the profile window.
        env: The current environment (e.g., 'AIR', 'PRO').
        num_scrolls: Number of scrolls to perform (for non-AIR envs).
        logger: Logger instance.
        console: Rich console instance.
        debug: Debug flag for conditional prints.

    Returns:
        A tuple containing the path to the stitched image (or None on error) 
        and the list of paths to the original screenshots.
    """
    screenshot_paths: List[str] = []
    try:
        x, y, width, height = bbox
        center_x = x + width // 2
        center_y = y + height // 2
        
        # Step 2: Begin screenshot capture process
        if debug:
            console.print("\n[bold]Step 2:[/bold] Capturing initial screenshot...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Ensure focus before initial capture
        pyautogui.moveTo(center_x, center_y, duration=0.5)
        pyautogui.click()
        time.sleep(1.0)
        # Add a small delay right before capturing to ensure stability
        time.sleep(0.2) 
        
        initial_path = take_high_quality_screenshot(bbox, 1, timestamp)
        screenshot_paths.append(initial_path)
        if debug:
            console.print(f"Initial screenshot saved to: {initial_path}")
        
        # Step 3 & 4: Capture subsequent screenshots
        if env == "AIR":
            if debug:
                console.print("\n[bold]Step 3:[/bold] Clicking for next photos...")
            for i in range(3): 
                if debug:
                    console.print(f"Clicking next photo ({i+1}/3)...")
                safe_click_x, safe_click_y = get_safe_coordinates(NEXT_PHOTO_POS[0], NEXT_PHOTO_POS[1])
                logger.debug(f"Attempting click at safe coordinates: ({safe_click_x}, {safe_click_y})")
                pyautogui.click(safe_click_x, safe_click_y)
                photo_click_delay = random.uniform(0.5, 1.5)
                logger.debug(f"Waiting {photo_click_delay:.2f}s before taking next photo...")
                time.sleep(photo_click_delay) # Random delay between clicks
                
                screenshot_number = i + 2
                screenshot_path = take_high_quality_screenshot(bbox, screenshot_number, timestamp)
                screenshot_paths.append(screenshot_path)
                if debug:
                    console.print(f"Screenshot {screenshot_number} saved to: {screenshot_path}")
        else:
            # Scrolling logic for non-AIR
            if debug:
                console.print("\n[bold]Step 3:[/bold] Scrolling and capturing profile...")
            perform_stepped_scroll(FIRST_SCROLL_AMOUNT)
            time.sleep(SCROLL_DELAY)
            
            screenshot_number = 2
            screenshot_path = take_high_quality_screenshot(bbox, screenshot_number, timestamp)
            screenshot_paths.append(screenshot_path)
            if debug:
                console.print(f"Screenshot {screenshot_number} saved to: {screenshot_path}")
            
            if debug:
                console.print("\n[bold]Step 4:[/bold] Continuing scroll and capture...")
            total_screenshots = num_scrolls + 1 # Recalculate for loop
            for i in range(num_scrolls - 1): 
                pyautogui.moveTo(center_x, center_y, duration=0.3)
                pyautogui.click()
                time.sleep(0.1)
                if debug:
                    console.print(f"Scroll {i+2}/{total_screenshots}: {SUBSEQUENT_SCROLL_AMOUNT} pixels...")
                perform_stepped_scroll(SUBSEQUENT_SCROLL_AMOUNT)
                time.sleep(SCROLL_DELAY)
                
                screenshot_number = i + 3
                screenshot_path = take_high_quality_screenshot(bbox, screenshot_number, timestamp)
                screenshot_paths.append(screenshot_path)
                if debug:
                    console.print(f"Screenshot {screenshot_number} saved to: {screenshot_path}")

            # Scroll back to top (only for non-AIR envs) - Moved from here
            # This should probably happen *after* processing the profile in the main loop
            # if the goal is to reset for the *next* profile in sequence.
            # Removing scroll-up from this function.
            pass # Placeholder for removed scroll-up logic

        # Stitch the images
        if debug:
            console.print("\nStitching screenshots...")
        stitch_layout = (2, 2) if env == "AIR" else (2, (num_scrolls + 1 + 1) // 2) # Dynamic layout
        stitched_path = stitch_images(
            screenshot_paths, 
            delete_originals=False, # Deletion handled by caller based on keep_screenshots
            layout=stitch_layout
        )
        if debug:
            console.print(f"Stitched image created: {stitched_path}")
        
        return stitched_path, screenshot_paths

    except Exception as e:
        logger.error("Error during screenshot capture or stitching", exc_info=True)
        console.print(f"[bold red]ERROR:[/bold red] Error capturing/stitching profile: {e}")
        return None, screenshot_paths # Return None for path, but paths list for potential cleanup 