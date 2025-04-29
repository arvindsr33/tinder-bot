"""Module for handling the like/pass decision process."""

import logging
from rich.console import Console
import pyautogui # Import pyautogui
import time      # Import time
import os        # Import os to check environment
import random    # Import random

# Import the function that calls the API (will be created in gpt.py)
from tinder_bot.gpt import like_or_pass 
# Import button coordinates and environment setting from scroll.py
from tinder_bot.scroll import LIKE_BUTTON, PASS_BUTTON, ENVIRONMENT, get_safe_coordinates

logger = logging.getLogger(__name__)
console = Console()

def like_photo(stitched_image_path: str, debug: bool):
    """
    Coordinates the process of deciding whether to like or pass a profile based on its image.
    First determines the final action ('LIKE' or 'PASS') considering AI input and probability rules.
    Then performs the click action only if ENVIRONMENT is AIR.
    
    Args:
        stitched_image_path: Path to the stitched profile image.
        debug: Boolean indicating if debug mode is active.
    """
    final_action = "PASS" # Default action, especially if errors occur early
    try:
        logger.info(f"Starting like/pass decision for image: {stitched_image_path}")
        
        # Step 1: Get AI decision
        decision = like_or_pass(stitched_image_path)
        
        # Step 2: Determine final action based on AI decision and rules
        if decision == "LIKE":
            like_probability = random.random() # Generate random float between 0.0 and 1.0
            if like_probability < 0.95: # 95% chance to actually LIKE
                final_action = "LIKE"
                console.print("[bold green]Decision: LIKE[/bold green]")
                logger.info(f"AI: LIKE, Probability < 0.95 ({like_probability:.2f}). Final Action: {final_action}")
            else: # 20% chance to PASS instead
                final_action = "PASS" # Override
                console.print("[bold green]Decision: LIKE[/bold green] -> [bold red](Override) PASS[/bold red]")
                logger.info(f"AI: LIKE, Probability >= 0.8 ({like_probability:.2f}). Overriding. Final Action: {final_action}")
        elif decision == "PASS":
            final_action = "PASS"
            console.print("[bold red]Decision: PASS[/bold red]")
            logger.info(f"AI: PASS. Final Action: {final_action}")
        else:
            # Handle unexpected responses from the API -> Default to PASS
            final_action = "PASS"
            console.print(f"[bold yellow]Warning:[/bold yellow] Unexpected decision from AI: '{decision}'. Defaulting to PASS.")
            logger.warning(f"Unexpected decision from AI: {decision}. Final Action: {final_action} (Fallback)")

        # Step 3: Execute the final action (Clicking or Placeholder)
        logger.info(f"Preparing to execute final action: {final_action}")
        if ENVIRONMENT == "AIR":
            if final_action == "LIKE":
                if LIKE_BUTTON:
                    safe_x, safe_y = get_safe_coordinates(LIKE_BUTTON[0], LIKE_BUTTON[1])
                    logger.info(f"Clicking LIKE button at safe coordinates: ({safe_x}, {safe_y})")
                    like_delay = random.uniform(1.0, 2.0)
                    logger.debug(f"Waiting {like_delay:.2f}s before clicking LIKE...")
                    time.sleep(like_delay)
                    pyautogui.click(safe_x, safe_y)
                    time.sleep(0.5) # Small delay after click
                else:
                    logger.warning("LIKE button coordinates not found, cannot perform LIKE action.")
                    console.print("[italic yellow]Placeholder: LIKE action intended, but LIKE_BUTTON not defined.[/italic yellow]")
            
            elif final_action == "PASS": # Covers decision == PASS, LIKE override, and unexpected fallback
                 if PASS_BUTTON:
                    safe_x, safe_y = get_safe_coordinates(PASS_BUTTON[0], PASS_BUTTON[1])
                    logger.info(f"Clicking PASS button at safe coordinates: ({safe_x}, {safe_y})")
                    pass_delay = random.uniform(1.0, 2.0)
                    logger.debug(f"Waiting {pass_delay:.2f}s before clicking PASS...")
                    time.sleep(pass_delay)
                    pyautogui.click(safe_x, safe_y)
                    time.sleep(0.5) # Small delay after click
                 else:
                    logger.warning("PASS button coordinates not found, cannot perform PASS action.")
                    console.print("[italic yellow]Placeholder: PASS action intended, but PASS_BUTTON not defined.[/italic yellow]")
        
        else: # Not AIR environment - print placeholder based on final_action
             console.print(f"[italic yellow]Placeholder: Final action is {final_action}. (Environment: {ENVIRONMENT})[/italic yellow]")

    except Exception as e:
        logger.error(f"Error during like/pass decision process for {stitched_image_path}: {e}", exc_info=True)
        console.print(f"[bold red]Error:[/bold red] Failed to make like/pass decision. See logs.")
        # Fallback action on error - still attempt to click PASS if possible in AIR env
        if ENVIRONMENT == "AIR" and PASS_BUTTON:
            try:
                safe_x, safe_y = get_safe_coordinates(PASS_BUTTON[0], PASS_BUTTON[1])
                logger.error(f"Error occurred. Clicking PASS as fallback at safe coordinates: ({safe_x}, {safe_y})")
                error_pass_delay = random.uniform(1.0, 2.0)
                logger.debug(f"Waiting {error_pass_delay:.2f}s before clicking PASS (error fallback)...")
                time.sleep(error_pass_delay)
                pyautogui.click(safe_x, safe_y)
                time.sleep(0.5)
            except Exception as click_err:
                 logger.error(f"Error attempting fallback PASS click: {click_err}", exc_info=True)
                 console.print("[bold red]Error:[/bold red] Failed during fallback PASS click.")
        else:
            # Log placeholder if not AIR or PASS_BUTTON is undefined during error
            console.print(f"[italic yellow]Placeholder: Defaulting to PASS action due to error, but cannot click (Env: {ENVIRONMENT}, PASS_BUTTON defined: {PASS_BUTTON is not None}).[/italic yellow]") 