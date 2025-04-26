"""Command-line interface for Hinge Bot."""

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

# Initialize Typer app
app = typer.Typer(help="Hinge Bot - Automated opener generator")

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
    use_stitched: bool = typer.Option(
        True, "--stitch/--no-stitch", help="Stitch screenshots into a single image for GPT-4o"
    ),
    send_message: bool = typer.Option(
        False, "--send/--no-send", help="Send the generated opener in Hinge"
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Run in debug mode with extra output"
    ),
    env: str = typer.Option(
        "MONITOR", "--env", "-e", help="Environment to use (MONITOR or MAC)"
    ),
    keep_screenshots: bool = typer.Option(
        False, "--keep-screenshots", help="Keep original screenshots after stitching"
    ),
    num_scrolls: int = typer.Option(
        5, "--num-scrolls", "-n", help="Number of scrolls to perform (default: 5)"
    )
):
    """
    Run the Hinge Bot to generate and optionally send openers.
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
    from tinder_bot.gpt import generate_opener
    from tinder_bot.message import send_opener
    from tinder_bot.image_utils import stitch_images
    
    # Import scroll constants and override NUM_SCROLLS
    from tinder_bot.scroll import (
        FIRST_SCROLL_AMOUNT, SUBSEQUENT_SCROLL_AMOUNT, SCROLL_DELAY, 
        UP_SCROLL_AMOUNT, STEPS_PER_SCROLL, perform_stepped_scroll
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
    
    console.print(f"[bold green]Hinge Bot[/bold green] - Starting up in {env} environment...")
    
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]ERROR:[/bold red] OPENAI_API_KEY not set. Please add it to your .env file.")
        raise typer.Exit(code=1)
    
    try:
        # Step 1: Find the iPhone window
        console.print("\n[bold]Step 1:[/bold] Finding iPhone window...")
        
        # Use get_hardcoded_window directly for MAC and MONITOR environments
        if env in ["MAC", "MONITOR"]:
            bbox = get_hardcoded_window()
            console.print(f"Using hardcoded {env} dimensions for iPhone window")
        else:
            # Fall back to visual detection for other environments
            bbox = find_iphone_window()
            
        if not bbox:
            console.print("[bold red]ERROR:[/bold red] Could not find iPhone window.")
            raise typer.Exit(code=1)
        
        x, y, width, height = bbox
        console.print(f"Found iPhone window at ({x}, {y}) with size {width}x{height}")
        center_x = x + width // 2
        center_y = y + height // 2
        console.print(f"Center point: ({center_x}, {center_y})")
        
        # Move to each corner of the window to visually verify position if in debug mode
        if debug:
            console.print("Moving cursor to window corners for verification...")
            # Top-left
            pyautogui.moveTo(x, y, duration=0.5)
            time.sleep(0.5)
            # Top-right
            pyautogui.moveTo(x + width, y, duration=0.5)
            time.sleep(0.5)
            # Bottom-right
            pyautogui.moveTo(x + width, y + height, duration=0.5)
            time.sleep(0.5)
            # Bottom-left
            pyautogui.moveTo(x, y + height, duration=0.5)
            time.sleep(0.5)
        
        # Step 2: Begin screenshot capture process
        console.print("\n[bold]Step 2:[/bold] Capturing initial screenshot...")
        screenshot_paths = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Move to center and click to ensure focus
        pyautogui.moveTo(center_x, center_y, duration=0.5)
        pyautogui.click()
        time.sleep(1.0)
        
        # Take initial high-quality screenshot using the direct region capture
        initial_path = take_high_quality_screenshot(bbox, 1, timestamp)
        screenshot_paths.append(initial_path)
        console.print(f"Initial screenshot saved to: {initial_path}")
        
        # Step 3: Scroll and capture more screenshots - we need exactly 5 scrolls for 6 total screenshots
        console.print("\n[bold]Step 3:[/bold] Scrolling and capturing profile...")
        
        # Use the stepped scroll function
        perform_stepped_scroll(FIRST_SCROLL_AMOUNT)
        
        # Wait for content to load
        time.sleep(SCROLL_DELAY)
        
        # Take screenshot
        screenshot_number = 2  # Screenshot 2
        screenshot_path = take_high_quality_screenshot(bbox, screenshot_number, timestamp)
        screenshot_paths.append(screenshot_path)
        console.print(f"Screenshot {screenshot_number} saved to: {screenshot_path}")
        
        # Step 4: Scroll and capture more screenshots - we need exactly 5 scrolls for 6 total screenshots
        console.print("\n[bold]Step 4:[/bold] Scrolling and capturing profile...")
        
        for i in range(num_scrolls - 1):  # Should be exactly 4 more scrolls
            # Move back to center and click to ensure focus before scrolling
            pyautogui.moveTo(center_x, center_y, duration=0.3)
            pyautogui.click()
            time.sleep(0.1)
            
            # Perform scroll with logging
            console.print(f"Scroll {i+2}/{total_screenshots}: {SUBSEQUENT_SCROLL_AMOUNT} pixels...")
            
            # Use the stepped scroll function
            perform_stepped_scroll(SUBSEQUENT_SCROLL_AMOUNT)
            
            # Wait for content to load
            time.sleep(SCROLL_DELAY)
            
            # Take screenshot
            screenshot_number = i + 3  # Screenshots 3-6
            screenshot_path = take_high_quality_screenshot(bbox, screenshot_number, timestamp)
            screenshot_paths.append(screenshot_path)
            console.print(f"Screenshot {screenshot_number} saved to: {screenshot_path}")
        
        # Scroll back to top for next profile
        console.print("\nScrolling back to top of profile...")
        
        # Calculate how many up-scrolls needed based on total distance scrolled
        total_scroll_distance = abs(FIRST_SCROLL_AMOUNT) + abs(SUBSEQUENT_SCROLL_AMOUNT) * (num_scrolls - 1)
        scrolls_needed = total_scroll_distance // abs(UP_SCROLL_AMOUNT) + 1
        
        # for i in range(scrolls_needed):
        #     pyautogui.click(center_x, center_y)
        #     time.sleep(0.1)
        #     console.print(f"Scroll up {i+1}/{scrolls_needed}: {UP_SCROLL_AMOUNT} pixels")
        #     perform_stepped_scroll(UP_SCROLL_AMOUNT)
        #     time.sleep(0.5)
        
        # Step 5: Stitch screenshots and generate opener using GPT-4o
        console.print("\n[bold]Step 5:[/bold] Generating opener with GPT-4o...")
        full_response = ""
        if use_stitched:
            console.print("Stitching screenshots into a single image...")
            
            # Stitch the images, but don't delete originals yet
            stitched_path = stitch_images(screenshot_paths, delete_originals=False, layout=layout)
            
            # Generate opener using the stitched image
            name, full_response = generate_opener(stitched_path)
            console.print(f"\n[bold green]Generated opener:[/bold green] {full_response}")
            
            # Prompt the user to enter their picked response
            picked_response = input("Enter the response you decided to pick: ")
            print(picked_response)

            # If the user wants to redo the opener, generate a new one
            if picked_response.strip().lower() == "redo":
                while picked_response.strip().lower() == "redo":
                    # Generate opener using the stitched image
                    name, full_response = generate_opener(stitched_path)
                    console.print(f"\n[bold green]Generated opener:[/bold green] {full_response}")
                    picked_response = input("Enter the response you decided to pick: ")
            

            # Append the picked response to the full response
            full_response += f"\n\nPicked: {picked_response}"
            
            # Create directory for today's profiles
            date_str = datetime.now().strftime("%Y%m%d")
            base_dir = Path(f"./screenshots/profile_{date_str}")
            base_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine file names based on the presence of a name
            name = name.strip().replace(" ", "_")
            profile_image_path = base_dir / f"profile_{name}.png"
            responses_file_path = base_dir / f"profile_{name}_responses.txt"
            
            # Check if the profile image path already exists
            if profile_image_path.exists():
                timestamp = datetime.now().strftime("%H%M%S")
                profile_image_path = base_dir / f"profile_{name}_{timestamp}.png"
                responses_file_path = base_dir / f"profile_{name}_{timestamp}_responses.txt"
            
            # Rename the stitched image
            stitched_path = Path(stitched_path)
            stitched_path.rename(profile_image_path)
            console.print(f"Stitched image saved as: {profile_image_path}")
            
            # Save the full response
            responses_file_path.write_text(full_response)
            console.print(f"Responses saved to: {responses_file_path}")
            
            # Delete original screenshots if not keeping them
            if not keep_screenshots:
                console.print("Deleting original screenshots...")
                deleted_count = delete_screenshots(screenshot_paths)
                console.print(f"Deleted {deleted_count} original screenshots")
        else:
            # Generate opener using individual screenshots
            name, full_response = generate_opener(screenshot_paths, use_stitched=False)
            console.print(f"\n[bold green]Generated opener:[/bold green] {full_response}")
        
        # Step 6: Send opener if requested
        if send_message:
            console.print("\n[bold]Step 6:[/bold] Sending opener in Hinge...")
            send_opener(full_response, bbox)
            console.print("[bold green]Opener sent successfully![/bold green]")
        
        console.print("\n[bold green]Done![/bold green] Hinge Bot completed successfully.")
        
    except Exception as e:
        logger.exception("Error during execution")
        console.print(f"\n[bold red]ERROR:[/bold red] {str(e)}")
        raise typer.Exit(code=1)

@app.command()
def version():
    """
    Display version information.
    """
    console.print("[bold green]Hinge Bot[/bold green] v0.1.0")
    console.print("A Python application that automates crafting personalized openers on Hinge.")

if __name__ == "__main__":
    app()