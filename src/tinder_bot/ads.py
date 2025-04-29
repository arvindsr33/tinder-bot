"""Module for checking if a profile view is an advertisement."""

import logging
from rich.console import Console
import os
from pathlib import Path
import time
from datetime import datetime

# Import necessary functions
from tinder_bot.gpt import gpt_check_ads 
from tinder_bot.scroll import get_hardcoded_window # To get window coords
from tinder_bot.capture import take_high_quality_screenshot # To take the screenshot

logger = logging.getLogger(__name__)
console = Console()


def check_for_ads(iteration_index: int, debug: bool) -> str:
    """
    Takes a screenshot, calls GPT to check if it's an ad, cleans up, and returns the result.

    Args:
        iteration_index: The current iteration number (used for temporary filename).
        debug: Boolean indicating if debug mode is active.

    Returns:
        str: "YES" if the AI determines it's an ad, "NO" otherwise.
             Returns "ERROR" if the API call or screenshot fails.
    """
    screenshot_path = None
    try:
        # 1. Get window dimensions
        bbox = get_hardcoded_window()
        if not bbox:
            logger.error("Failed to get window dimensions for ad check.")
            return "ERROR"
        
        # 2. Define timestamp (needed for the function call)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # Use timestamp for uniqueness
        screenshot_dir = Path("./screenshots")
        screenshot_dir.mkdir(exist_ok=True) # Ensure directory exists
        # The function will construct the path, so we don't define screenshot_path here yet.

        # 3. Take a single screenshot using the correct arguments
        logger.info(f"Taking temporary screenshot for ad check (iteration {iteration_index})")
        # Pass bbox, index, timestamp, and the target directory
        screenshot_path_str = take_high_quality_screenshot(bbox, iteration_index, timestamp, output_dir=str(screenshot_dir))
        screenshot_path = Path(screenshot_path_str) # Convert returned string path to Path object
        time.sleep(0.5) # Brief pause after screenshot

        # 4. Call GPT for ad check
        logger.info(f"Checking image for ads: {screenshot_path}")
        decision = gpt_check_ads(str(screenshot_path))
        
        # 5. Process decision
        if decision == "YES":
            # Only print this if CLI isn't already printing the action
            # Since CLI prints "Ad detected. Performing PASS action.", we can remove this one
            # if debug: 
            #    console.print("[bold yellow]Ad detected.[/bold yellow]")
            logger.info("AI determined the image is an advertisement.")
            return "YES"
        elif decision == "NO":
            # No need to print anything if it's not an ad
            logger.info("AI determined the image is not an advertisement.")
            return "NO"
        else: # Handle API errors or unexpected responses
             logger.error(f"Ad check failed with status: {decision}")
             console.print(f"[bold red]Error:[/bold red] Failed to check for ads (Status: {decision}). Assuming not an ad.")
             return "ERROR" # Indicate an error occurred

    except Exception as e:
        logger.error(f"Unexpected error during ad check process: {e}", exc_info=True)
        console.print(f"[bold red]Error:[/bold red] Unexpected error during ad check. Assuming not an ad.")
        return "ERROR"
    finally:
        # 6. Clean up screenshot regardless of outcome
        if screenshot_path and screenshot_path.exists():
            try:
                os.remove(screenshot_path)
                logger.debug(f"Deleted temporary ad check screenshot: {screenshot_path}")
            except OSError as e:
                logger.warning(f"Could not delete temporary ad check screenshot {screenshot_path}: {e}") 