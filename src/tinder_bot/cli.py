"""Command-line interface for Tinder Bot."""

import typer
import logging
import os
from rich.console import Console
from rich.logging import RichHandler
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
import time
import pyautogui
import glob # Import glob
import random # Import random

# Initialize Typer app
app = typer.Typer(help="Tinder Bot - Automated opener generator")

# Load environment variables
load_dotenv()
NUM_SCROLLS = int(os.getenv("NUM_SCROLLS", 5))
NUM_COLS = NUM_SCROLLS // 2
LAYOUT = (2, NUM_COLS)

# Configure logging
console = Console()

def setup_logging():
    """Set up logging with Rich handler."""
    log_level = os.getenv("LOG_LEVEL", "ERROR")
    log_dir = os.getenv("LOG_DIR", "./logs")
    
    # Create log directory if it doesn't exist
    Path(log_dir).mkdir(exist_ok=True)
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"tinder_bot_{timestamp}.log"
    
    # Get the numeric log level
    numeric_level = getattr(logging, log_level)
    
    # Create handlers with the correct level
    rich_handler = RichHandler(console=console, rich_tracebacks=True, level=numeric_level)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(numeric_level)
    
    # Configure the root logger - this affects ALL loggers in the application
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[rich_handler, file_handler]
    )
    
    # Make sure the root logger level is set
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Also make sure all existing handlers have their levels set
    for handler in root_logger.handlers:
        handler.setLevel(numeric_level)
    
    # Explicitly set the level for the tinder_bot package loggers
    tinder_bot_logger = logging.getLogger("tinder_bot")
    tinder_bot_logger.setLevel(numeric_level)
    
    # Also set levels for specific module loggers
    module_loggers = [
        logging.getLogger("tinder_bot.gpt"),
        logging.getLogger("tinder_bot.window"),
        logging.getLogger("tinder_bot.scroll"),
        logging.getLogger("tinder_bot.capture"),
        logging.getLogger("tinder_bot.image_utils"),
        logging.getLogger("httpx")  # Also silence the httpx library if needed
    ]
    
    for logger in module_loggers:
        logger.setLevel(numeric_level)
        # Also set the level on all handlers attached to each logger
        for handler in logger.handlers:
            handler.setLevel(numeric_level)
    
    # Also explicitly disable propagation for these loggers if needed
    # This prevents log messages from being handled by parent loggers
    # Uncomment if you're still seeing unwanted logs
    # for logger in module_loggers:
    #     logger.propagate = False
    
    return tinder_bot_logger

@app.command()
def run(
    mode: str = typer.Option(
        "opener", "--mode", "-m", help="Operation mode: 'opener' (generate openers) or 'like' (decide like/pass)"
    ),
    send_message: bool = typer.Option(
        False, "--send/--no-send", help="Send the generated opener in Tinder (only applies if mode='opener')"
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Run in debug mode with extra output"
    ),
    env: str = typer.Option(
        "MONITOR", "--env", "-e", help="Environment to use (MONITOR, PRO, or AIR)"
    ),
    keep_screenshots: bool = typer.Option(
        False, "--keep-screenshots", help="Keep original screenshots after stitching"
    ),
    num_scrolls: int = typer.Option(
        4, "--num-scrolls", "-n", help="Number of scrolls to perform (default: 5)"
    ),
    duration: int = typer.Option(
        15, "--duration", "-d", help="Maximum duration in minutes to run the 'like' mode (default: 15)"
    )
):
    """
    Run the Tinder Bot to generate and optionally send openers.
    """
    # Set environment variables for the session before importing any modules that use them
    os.environ["ENVIRONMENT"] = env
    os.environ["DEBUG_SCROLL"] = str(debug).lower()
    
    # Calculate layout based on num_scrolls
    total_screenshots = num_scrolls + 1  # Add 1 for the initial screenshot
    num_cols = (total_screenshots + 1) // 2  # Ensure we have enough columns
    layout = (2, num_cols)
    
    # Now import the modules that depend on environment variables
    from tinder_bot.window import find_iphone_window, save_detected_window
    from tinder_bot.capture import take_high_quality_screenshot, delete_screenshots
    from tinder_bot.scroll import scroll_profile, get_hardcoded_window
    from tinder_bot.gpt import generate_opener # Import will be conditional later
    from tinder_bot.like import like_photo # Import the new like function
    from tinder_bot.message import send_opener
    from tinder_bot.image_utils import stitch_images
    # Import the profile processor
    from tinder_bot.profile_processor import process_single_profile 
    # Import the ad checker
    from tinder_bot.ads import check_for_ads 
    
    # Import scroll constants and override NUM_SCROLLS
    from tinder_bot.scroll import (
        FIRST_SCROLL_AMOUNT, SUBSEQUENT_SCROLL_AMOUNT, SCROLL_DELAY, 
        UP_SCROLL_AMOUNT, STEPS_PER_SCROLL, perform_stepped_scroll, NEXT_PHOTO_POS,
        PASS_BUTTON, LIKE_BUTTON, get_safe_coordinates, ENVIRONMENT # Import button coords and env
    )
    import tinder_bot.scroll as scroll
    scroll.NUM_SCROLLS = num_scrolls

    # Set up logging
    logger = setup_logging()
    
    if debug:
        # Set DEBUG level for all loggers in the application
        debug_level = logging.DEBUG
        
        # Set the level for the root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(debug_level)
        
        # Set the level for all handlers
        for handler in root_logger.handlers:
            handler.setLevel(debug_level)
        
        # Set the level for our main logger
        logger.setLevel(debug_level)
        
        # Set the level for all handlers on our main logger
        for handler in logger.handlers:
            handler.setLevel(debug_level)
        
        logger.debug("Debug mode enabled")
    
    console.print(f"[bold green]Tinder Bot[/bold green] - Starting up in {env} environment...")
    
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]ERROR:[/bold red] OPENAI_API_KEY not set. Please add it to your .env file.")
        raise typer.Exit(code=1)
    
    try:
        # Step 1.5: Clear old screenshots from root directory (runs once before loop/main action)
        console.print("\n[bold]Step 1.5:[/bold] Clearing old screenshots from root directory...")
        screenshots_dir = Path("./screenshots")
        screenshots_dir.mkdir(exist_ok=True) # Ensure directory exists
        old_screenshots = glob.glob(str(screenshots_dir / "*.png"))
        deleted_count = 0
        if old_screenshots:
            console.print(f"Found {len(old_screenshots)} old screenshots to clear...")
            for f_path in old_screenshots:
                try:
                    os.remove(f_path)
                    deleted_count += 1
                    logger.debug(f"Deleted old screenshot: {f_path}")
                except OSError as e:
                    logger.warning(f"Could not delete old screenshot {f_path}: {e}")
            console.print(f"Cleared {deleted_count} old screenshots.")
        else:
            console.print("No old screenshots found in root directory to clear.")

        # --- Decide Action based on Mode --- 
        if mode == "like":
            num_iterations = random.randint(50, 100)
            console.print(f"\n[bold]Running LIKE mode for {num_iterations} iterations or max {duration} minutes...[/bold]")
            
            start_time = time.time()
            end_time = start_time + duration * 60
            iterations_completed = 0 # Keep track of actual iterations done
            
            for i in range(num_iterations):
                # --- Time Check --- 
                if time.time() >= end_time:
                    console.print(f"\n[bold]Time limit ({duration} minutes) reached. Stopping early.[/bold]")
                    break # Exit the loop if duration exceeded
                # ------------------
                
                console.rule(f"Iteration {i+1}/{num_iterations} (Time left: {max(0, int(end_time - time.time()))}s)")
                try:
                    # Step 0: Check for Ads 
                    if debug:
                        console.print("\n[bold]Step 0:[/bold] Checking for advertisements...")
                    # Pass debug flag to ad checker
                    ad_result = check_for_ads(i + 1, debug)
                    
                    # If it's an ad, PASS and skip
                    if ad_result == "YES":
                        # Keep this message as it indicates a specific action/decision
                        console.print("[bold yellow]Ad detected. Performing PASS action.[/bold yellow]") 
                        if ENVIRONMENT == "AIR" and PASS_BUTTON:
                            try:
                                safe_x, safe_y = get_safe_coordinates(PASS_BUTTON[0], PASS_BUTTON[1])
                                logger.info(f"Clicking PASS button (ad detected) at safe coordinates: ({safe_x}, {safe_y})")
                                pass_delay = random.uniform(1.0, 2.0)
                                logger.debug(f"Waiting {pass_delay:.2f}s before clicking PASS (ad)...")
                                time.sleep(pass_delay)
                                pyautogui.click(safe_x, safe_y)
                                time.sleep(0.5) # Small delay after click
                            except Exception as click_err:
                                logger.error(f"Error clicking PASS for ad: {click_err}", exc_info=True)
                                console.print(f"[bold red]Error:[/bold red] Failed PASS click for ad.")
                        else:
                            if debug: # Only show placeholder if debugging
                                console.print(f"[italic yellow]Placeholder: PASS action for ad (Env: {ENVIRONMENT}, Button defined: {PASS_BUTTON is not None}).[/italic yellow]")
                        
                        # Pause and continue
                        pause_duration = random.uniform(2.0, 3.0)
                        if debug:
                            console.print(f"\n--- Ad handled. Pausing for {pause_duration:.2f} seconds before next iteration... ---")
                        time.sleep(pause_duration)
                        continue
                    elif ad_result == "ERROR":
                        # Keep this warning
                        console.print("[bold yellow]Warning:[/bold yellow] Ad check failed. Proceeding with profile processing.")
                        logger.warning("Ad check resulted in ERROR, proceeding with normal like/pass flow.")
                    else: # ad_result == "NO"
                        if debug:
                            console.print("No ad detected. Proceeding with profile processing.")
                    
                    # Step 1-4: Process profile 
                    if debug:
                        console.print("\n[bold]Step 1-4:[/bold] Processing profile (capture & stitch)...")
                    # Get window coords 
                    bbox = get_hardcoded_window() # Needed for profile_processor
                    # Pass debug flag to profile processor
                    stitched_path, _ = process_single_profile(
                        env=env, 
                        num_scrolls=num_scrolls, 
                        logger=logger, 
                        console=console, 
                        keep_screenshots=keep_screenshots,
                        debug=debug # Pass the flag
                    )

                    if not stitched_path:
                        console.print("[bold red]ERROR:[/bold red] Failed to process profile for this iteration.")
                        time.sleep(random.uniform(2.0, 3.0))
                        continue 
                    
                    if debug:
                        console.print(f"Stitched profile image: {stitched_path}")

                    # Step 5: Decide Like/Pass
                    if debug:
                        console.print("\n[bold]Step 5:[/bold] Deciding Like/Pass...")
                    # Pass debug flag to like_photo
                    like_photo(stitched_path, debug)
                except Exception as iter_e:
                     logger.error(f"An unexpected error occurred during iteration {i+1}", exc_info=True)
                     console.print(f"[bold red]ERROR:[/bold red] Unexpected error during iteration {i+1}: {iter_e}")
                     console.print("Attempting to continue to the next iteration...")

                iterations_completed += 1 # Increment counter only if iteration finishes (or before sleep)
                # Pause between iterations
                pause_duration = random.uniform(2.0, 3.0)
                # Check time again before sleeping long
                if time.time() + pause_duration >= end_time:
                    console.print(f"\n--- Iteration {i+1} complete. Time limit reached during pause. Finishing... ---")
                    # No need to break here as the check at the start of the next loop will catch it, or the loop ends
                    # Or we could break here to be absolutely sure: break
                
                if debug:
                    console.print(f"\n--- Iteration {i+1} complete. Pausing for {pause_duration:.2f} seconds... ---")
                time.sleep(pause_duration)
            
            # Print final status
            elapsed_time = time.time() - start_time
            if iterations_completed < num_iterations:
                console.print(f"\n[bold]Like mode finished early due to time limit ({duration} min). Ran for {elapsed_time:.2f}s, completed {iterations_completed}/{num_iterations} iterations.[/bold]")
            else:
                 console.print(f"\n[bold]Like mode finished all {num_iterations} iterations in {elapsed_time:.2f}s (within {duration} min limit).[/bold]")

        elif mode == "opener":
            # --- Opener Mode Logic (Runs Once) ---
            # Step 1-4: Process profile (capture & stitch)
            console.print("\n[bold]Step 1-4:[/bold] Processing profile (capture & stitch)...")
            stitched_path, bbox = process_single_profile(
                env=env, 
                num_scrolls=num_scrolls, 
                logger=logger, 
                console=console, 
                keep_screenshots=keep_screenshots
            )

            if not stitched_path or not bbox:
                console.print("[bold red]ERROR:[/bold red] Failed to process profile.")
                raise typer.Exit(code=1)

            x, y, width, height = bbox
            center_x = x + width // 2
            center_y = y + height // 2
            console.print(f"Profile processed. Using window at ({x}, {y}) size {width}x{height}")
            console.print(f"Stitched profile image: {stitched_path}")

            # Step 5: Generate opener 
            # The stitching is done inside process_single_profile now
            console.print("\n[bold]Step 5:[/bold] Generating opener with GPT-4o...")
            full_response = ""
            opener = ""
            name = "unknown" # Default name
            
            # Generate opener using the stitched image
            name, full_response = generate_opener(stitched_path)
            console.print(f"\n[bold green]Generated opener:[/bold green] {full_response}")
            
            # Prompt the user to enter their picked response
            # Extract just the first line as the potential opener to send
            if full_response:
                opener = full_response.split('\n')[0].strip()
                if opener.startswith("-"):
                    opener = opener.split(":", 1)[-1].strip()

            picked_response = input(f"Suggested: '{opener}'\nEnter the response you decided to pick (or 'redo'): ")
            
            # If the user wants to redo the opener, generate a new one
            while picked_response.strip().lower() == "redo":
                name, full_response = generate_opener(stitched_path)
                console.print(f"\n[bold green]Generated opener:[/bold green] {full_response}")
                if full_response:
                    opener = full_response.split('\n')[0].strip()
                    if opener.startswith("-"):
                        opener = opener.split(":", 1)[-1].strip()
                picked_response = input(f"Suggested: '{opener}'\nEnter the response you decided to pick (or 'redo'): ")
            
            # Use the user's picked response if provided, otherwise use the first generated line
            final_opener_to_send = picked_response if picked_response else opener

            # Append the picked response info to the full response for saving
            full_response_to_save = full_response + f"\n\nPicked: {final_opener_to_send}"
            
            # --- Save results (common logic, maybe refactor later) ---
            date_str = datetime.now().strftime("%Y%m%d")
            base_dir = Path(f"./screenshots/profile_{date_str}")
            base_dir.mkdir(parents=True, exist_ok=True)
            
            name = name.strip().replace(" ", "_") # Sanitize name for filename
            profile_image_path = base_dir / f"profile_{name}.png"
            responses_file_path = base_dir / f"profile_{name}_responses.txt"
            
            # Handle potential filename collisions
            if profile_image_path.exists():
                timestamp_suffix = datetime.now().strftime("%H%M%S")
                profile_image_path = base_dir / f"profile_{name}_{timestamp_suffix}.png"
                responses_file_path = base_dir / f"profile_{name}_{timestamp_suffix}_responses.txt"
            
            # Rename stitched image and save response
            Path(stitched_path).rename(profile_image_path)
            console.print(f"Stitched image saved as: {profile_image_path}")
            responses_file_path.write_text(full_response_to_save)
            console.print(f"Responses saved to: {responses_file_path}")
            # --- End Save results --- 

            # Original screenshot deletion is handled by process_single_profile now
            # if not keep_screenshots:
            #     console.print("Deleting original screenshots...")
            #     # Need the original paths if we want to delete here, but let process_single_profile handle it
            #     # deleted_count = delete_screenshots(screenshot_paths) 
            #     # console.print(f"Deleted {deleted_count} original screenshots")
            #     pass # Deletion handled earlier
            logger.info(f"Generated opener using stitched image: {profile_image_path}")
            
            console.print("\n[bold]Opener to send:[/bold]")
            console.print(final_opener_to_send if final_opener_to_send else "[yellow]No opener generated/picked.[/yellow]")
            
            # Optionally send the message
            if send_message and final_opener_to_send:
                console.print("\n[bold]Step 6:[/bold] Sending opener in Tinder...")
                send_opener(final_opener_to_send, bbox)
                logger.info("Sent opener to Tinder")
        
        else:
             console.print(f"[bold red]Error:[/bold red] Invalid mode '{mode}'. Choose 'opener' or 'like'.")
             raise typer.Exit(code=1)

        console.print("\n[bold green]Done![/bold green] Tinder Bot completed successfully.")
        
    except Exception as e:
        logger.error("An unexpected error occurred", exc_info=True)
        console.print(f"[bold red]ERROR:[/bold red] An unexpected error occurred: {e}")
        raise typer.Exit(code=1)

@app.command()
def version():
    """Display version information."""
    console.print("[bold green]Tinder Bot[/bold green] v0.1.0")
    console.print("A Python application that automates crafting personalized openers on Tinder.")

@app.command()
def analyze_profile():
    # Implementation of analyze_profile command
    console.print("[bold green]Analyzing profile...[/bold green]")
    # Add your implementation here

if __name__ == "__main__":
    app()