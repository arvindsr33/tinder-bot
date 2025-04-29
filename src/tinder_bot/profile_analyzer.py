"""Profile analysis script for Tinder Bot."""

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
import random
from typing import List

# Initialize Typer app
app = typer.Typer(help="Tinder Profile Analyzer - Get personalized profile improvement suggestions")

# Load environment variables
load_dotenv()

# Configure logging
console = Console()

# Constants
NUM_MY_PROFILE_SCROLLS = 7  # For 8 total screenshots
STITCHED_DIR = "screenshots/stitched"
MY_PROFILE_DIR = "screenshots/my_profile"
MAX_COMPARISON_PROFILES = 20

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
    
    # Get the logger for this module
    logger = logging.getLogger(__name__)
    logger.setLevel(numeric_level)
    
    return logger

@app.command()
def analyze(
    debug: bool = typer.Option(
        False, "--debug", help="Run in debug mode with extra output"
    ),
    env: str = typer.Option(
        "MONITOR", "--env", help="Environment to use (MONITOR or MAC)"
    ),
    num_comparisons: int = typer.Option(
        10, "--num-comparisons", "-n", help="Number of profiles to compare against (max 20)"
    ),
    use_existing: bool = typer.Option(
        False, "--use-existing", help="Use the latest profile from screenshots/my_profile instead of capturing new screenshots"
    )
):
    """
    Analyze your Tinder profile and get improvement suggestions.
    """
    # Set environment variables
    os.environ["ENVIRONMENT"] = env
    os.environ["DEBUG_SCROLL"] = str(debug).lower()
    
    # Set up logging BEFORE importing modules
    logger = setup_logging()
    
    # Import dependencies after setting environment variables
    from tinder_bot.window import find_iphone_window
    from tinder_bot.capture import take_high_quality_screenshot, delete_screenshots
    from tinder_bot.scroll import (
        FIRST_SCROLL_AMOUNT, SUBSEQUENT_SCROLL_AMOUNT, SCROLL_DELAY,
        UP_SCROLL_AMOUNT, STEPS_PER_SCROLL, perform_stepped_scroll, get_hardcoded_window
    )
    from tinder_bot.gpt import generate_opener
    from tinder_bot.image_utils import stitch_images

    # Ensure directories exist
    Path(MY_PROFILE_DIR).mkdir(parents=True, exist_ok=True)
    
    console.print("[bold green]Tinder Profile Analyzer[/bold green] - Starting up...")
    
    # Verify OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]ERROR:[/bold red] OPENAI_API_KEY not set. Please add it to your .env file.")
        raise typer.Exit(code=1)
    
    try:
        my_profile_stitched = None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Move timestamp here so it's available for both paths
        
        # Check for existing profile if requested
        if use_existing:
            console.print("\n[bold]Checking for existing profile...[/bold]")
            existing_profiles = list(Path(MY_PROFILE_DIR).glob("profile_stitched_*.png"))
            
            if existing_profiles:
                # Get the most recent stitched profile
                latest_profile = max(existing_profiles, key=lambda p: p.stat().st_mtime)
                my_profile_stitched = str(latest_profile)
                console.print(f"Found existing profile: {latest_profile.name}")
            else:
                console.print("[yellow]No existing profile found. Will capture new screenshots.[/yellow]")
                use_existing = False
        
        # Only capture new screenshots if we're not using an existing profile
        if not use_existing:
            # Step 1: Wait for user to navigate to their profile
            console.print("\n[bold yellow]Please navigate to your Tinder profile.[/bold yellow]")
            input("Press Enter when ready...")
            
            # Step 2: Find the iPhone window
            console.print("\n[bold]Step 1:[/bold] Finding iPhone window...")
            
            if env in ["MAC", "MONITOR"]:
                bbox = get_hardcoded_window()
                console.print(f"Using hardcoded {env} dimensions for iPhone window")
            else:
                bbox = find_iphone_window()
                
            if not bbox:
                console.print("[bold red]ERROR:[/bold red] Could not find iPhone window.")
                raise typer.Exit(code=1)
            
            x, y, width, height = bbox
            center_x = x + width // 2
            center_y = y + height // 2
            
            # Step 3: Capture profile screenshots
            console.print("\n[bold]Step 2:[/bold] Capturing your profile...")
            screenshot_paths = []
            
            # Take initial screenshot
            initial_path = take_high_quality_screenshot(bbox, 1, timestamp, output_dir=MY_PROFILE_DIR)
            screenshot_paths.append(initial_path)
            
            # Scroll and capture remaining screenshots
            for i in range(NUM_MY_PROFILE_SCROLLS):
                scroll_amount = FIRST_SCROLL_AMOUNT if i == 0 else SUBSEQUENT_SCROLL_AMOUNT
                
                # Ensure focus and scroll
                pyautogui.moveTo(center_x, center_y, duration=0.3)
                pyautogui.click()
                time.sleep(0.1)
                
                console.print(f"Scroll {i+1}/{NUM_MY_PROFILE_SCROLLS}: {scroll_amount} pixels...")
                perform_stepped_scroll(scroll_amount)
                time.sleep(SCROLL_DELAY)
                
                # Capture screenshot
                screenshot_number = i + 2
                screenshot_path = take_high_quality_screenshot(
                    bbox, screenshot_number, timestamp, output_dir=MY_PROFILE_DIR
                )
                screenshot_paths.append(screenshot_path)
            
            # Step 4: Stitch your profile screenshots (2x4 layout)
            console.print("\n[bold]Step 3:[/bold] Creating profile composite...")
            my_profile_stitched = stitch_images(
                screenshot_paths,
                output_dir=MY_PROFILE_DIR,
                layout=(2, 4),  # 2 rows, 4 columns for 8 screenshots
                delete_originals=True
            )
        
        # From here, the code continues with comparison and analysis
        # regardless of whether we used an existing profile or captured new screenshots
        
        # Step 5: Get random sample of other profiles
        console.print("\n[bold]Step 4:[/bold] Selecting comparison profiles...")
        stitched_profiles = list(Path(STITCHED_DIR).glob("*.png"))
        num_comparisons = min(num_comparisons, len(stitched_profiles), MAX_COMPARISON_PROFILES)
        
        if not stitched_profiles:
            console.print("[yellow]Warning: No comparison profiles found in screenshots/stitched[/yellow]")
            comparison_paths = []
        else:
            comparison_paths = random.sample(stitched_profiles, num_comparisons)
            console.print(f"Selected {len(comparison_paths)} profiles for comparison")
        
        # Step 6: Generate analysis with GPT-4o
        console.print("\n[bold]Step 5:[/bold] Generating profile analysis...")
        
        # Prepare prompt for profile analysis
        ANALYSIS_PROMPT = f"""
        You're a helpful dating coach who enjoys young people in finding suitable partners and bringing them together.
        I'm showing you {num_comparisons + 1} Tinder dating profiles:
        1. The first image is the profile of the candidate that needs improvement
        2. The remaining {num_comparisons} images are profiles of people the candidate deserves based on the hard work he has done in his life and career.
        
        Please analyze the candidate's profile and provide detailed suggestions for improvement:
        1. Photo Analysis & Suggestions
           - What works well in the candidate's current photos
           - Specific ideas for new photos (poses, activities, settings)
           - Style and presentation tips
           
        2. Prompt Analysis & Suggestions
           - How effective are the candidate's current prompts
           - Ideas for better prompt responses
           - What topics/interests to highlight
           
        3. Overall Profile Strategy
           - How well does the candidate's profile appeal to the target audience
           - Key areas for improvement
           - Specific action items prioritized by impact
           
        Base your suggestions on what works well in the comparison profiles while maintaining authenticity. Please help. Don't deny the candidate's hard work.
        """
        
        # Send all images to GPT-4o
        all_images = [my_profile_stitched] + [str(p) for p in comparison_paths]
        name, full_response = generate_opener(all_images, use_stitched=False)
        
        # Create directory for today's profiles
        date_str = datetime.now().strftime("%Y%m%d")
        base_dir = Path(f"./screenshots/profile_{date_str}")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine file names based on the presence of a name
        if name != "unknown":
            profile_image_path = base_dir / f"profile_{name}.png"
            analysis_file_path = base_dir / f"profile_{name}_responses.txt"
        else:
            profile_image_path = base_dir / Path(my_profile_stitched).name
            analysis_file_path = base_dir / f"{Path(my_profile_stitched).stem}_responses.txt"
        
        # Rename the stitched image
        Path(my_profile_stitched).rename(profile_image_path)
        console.print(f"Stitched image saved as: {profile_image_path}")
        
        # Save the full response
        analysis_file_path.write_text(full_response)
        console.print(f"Analysis saved to: {analysis_file_path}")
        
        console.print("\n[bold green]Done![/bold green] Profile analysis completed successfully.")
        
    except Exception as e:
        logger.exception("Error during execution")
        console.print(f"\n[bold red]ERROR:[/bold red] {str(e)}")
        raise typer.Exit(code=1)

@app.command()
def version():
    """Print the version number."""
    console.print("[bold green]Tinder Profile Analyzer[/bold green] v0.1.0")
    console.print("A tool for analyzing and improving your Tinder dating profile.")

if __name__ == "__main__":
    app() 