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
    Prints the AI's reason for the decision.
    
    Args:
        stitched_image_path: Path to the stitched profile image.
        debug: Boolean indicating if debug mode is active.
    """
    final_action = "PASS" # Default action, especially if errors occur early
    ai_reason = "(Decision process failed early)" # Default reason
    try:
        logger.info(f"Starting like/pass decision for image: {stitched_image_path}")
        
        # Step 1: Get AI decision and reason
        # like_or_pass now returns a tuple (decision, reason)
        ai_decision, ai_reason = like_or_pass(stitched_image_path)
        
        # Step 2: Determine final action based on AI decision and rules
        if ai_decision == "LIKE":
            like_probability = random.random() # Generate random float between 0.0 and 1.0
            if like_probability < 0.95: # 95% chance to actually LIKE
                final_action = "LIKE"
                # Print decision and reason
                console.print(f"[bold green]Decision: LIKE[/bold green] - Reason: {ai_reason}")
                logger.info(f"AI: LIKE (Reason: {ai_reason}), Probability < 0.95 ({like_probability:.2f}). Final Action: {final_action}")
            else: # 5% chance to PASS instead
                final_action = "PASS" # Override
                # Print decision, override, and reason
                console.print(f"[bold green]Decision: LIKE[/bold green] -> [bold red](Override) PASS[/bold red] - Reason: {ai_reason}")
                logger.info(f"AI: LIKE (Reason: {ai_reason}), Probability >= 0.95 ({like_probability:.2f}). Overriding. Final Action: {final_action}")
        elif ai_decision == "PASS":
            final_action = "PASS"
            # Print decision and reason
            console.print(f"[bold red]Decision: PASS[/bold red] - Reason: {ai_reason}")
            logger.info(f"AI: PASS (Reason: {ai_reason}). Final Action: {final_action}")
        else: # This case should technically not be reached if like_or_pass always returns LIKE/PASS
              # But keeping it as a safeguard. ai_decision might contain error info if tuple return failed (though unlikely now)
            final_action = "PASS"
            console.print(f"[bold yellow]Warning:[/bold yellow] Unexpected state after AI decision ('{ai_decision}'). Defaulting to PASS. Detail: {ai_reason}")
            logger.warning(f"Unexpected state after AI decision: {ai_decision}. Reason/Detail: {ai_reason}. Final Action: {final_action} (Fallback)")

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
        # Print error and the last known reason (which might be the default or from the API call error)
        console.print(f"[bold red]Error:[/bold red] Failed to make like/pass decision. See logs. Last recorded reason/detail: {ai_reason}")
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