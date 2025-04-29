"""Profile scrolling module for navigating Tinder profiles."""

from typing import Tuple, Optional
import pyautogui
import time
import logging
import os

logger = logging.getLogger(__name__)

# Constants for scrolling behavior
FIRST_SCROLL_AMOUNT = -520  # First scroll amount (negative for downward)
SUBSEQUENT_SCROLL_AMOUNT = -720  # Subsequent scroll amount
SCROLL_DELAY = 0.2  # Fixed 0.5 second delay between scrolls
NUM_SCROLLS = int(os.getenv("NUM_SCROLLS", 5))  
UP_SCROLL_AMOUNT = 600  # For scrolling back up

# Small steps settings
STEPS_PER_SCROLL = 10  # Break each scroll into 10 smaller steps
STEP_DELAY = 0.01  # Small delay between steps

# Click position for AIR environment (initialized, set below)
NEXT_PHOTO_POS: Optional[Tuple[int, int]] = None 

# Like/Pass button positions for AIR environment (initialized, set below)
LIKE_BUTTON: Optional[Tuple[int, int]] = None
PASS_BUTTON: Optional[Tuple[int, int]] = None

# Hardcoded screen dimensions based on environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "MONITOR")

# Screen configuration based on environment
if ENVIRONMENT == "MONITOR":
    # Default monitor configuration
    SCREEN_WIDTH = 2511
    SCREEN_HEIGHT = 1051
    
    # iPhone window position and size
    IPHONE_X_BEGIN = 2304
    IPHONE_Y_BEGIN = 617
    IPHONE_X_END = 2500
    IPHONE_Y_END = 1042
    
    # Calculate width and height
    IPHONE_WIDTH = IPHONE_X_END - IPHONE_X_BEGIN
    IPHONE_HEIGHT = IPHONE_Y_END - IPHONE_Y_BEGIN
    
elif ENVIRONMENT == "PRO":
    # MacBook Pro configuration using provided coordinates
    # Set screen dimensions based on actual Mac screen
    SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()
    
    # iPhone window position and size based on provided coordinates
    IPHONE_X_BEGIN = 935  # Top-left X coordinate
    IPHONE_Y_BEGIN = 330  # Top-left Y coordinate
    IPHONE_X_END = 1139  # Bottom-right X coordinate
    IPHONE_Y_END = 739    # Bottom-right Y coordinate
    
    # Calculate width and height
    IPHONE_WIDTH = IPHONE_X_END - IPHONE_X_BEGIN
    IPHONE_HEIGHT = IPHONE_Y_END - IPHONE_Y_BEGIN
    
    logger.info(f"Using PRO configuration with iPhone dimensions: {IPHONE_WIDTH}x{IPHONE_HEIGHT}")
    logger.info(f"iPhone position: ({IPHONE_X_BEGIN}, {IPHONE_Y_BEGIN}) to ({IPHONE_X_END}, {IPHONE_Y_END})")

elif ENVIRONMENT == "AIR":
    # MacBook Air configuration (PLACEHOLDER - UPDATE THESE VALUES)
    # Set screen dimensions based on actual Mac screen
    SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()

    # iPhone window position and size (PLACEHOLDER VALUES)
    IPHONE_X_BEGIN = 815  # Top-left X coordinate (UPDATE ME)
    IPHONE_Y_BEGIN = 260  # Top-left Y coordinate (UPDATE ME)
    IPHONE_X_END = 1018 # Bottom-right X coordinate (UPDATE ME)
    IPHONE_Y_END = 575   # Bottom-right Y coordinate (UPDATE ME)
    
    # Position to click for next photo
    NEXT_PHOTO_POS = (974, 410)

    # Like/Pass button coordinates for AIR
    LIKE_BUTTON = (955, 580)
    PASS_BUTTON = (880, 580)

    # Calculate width and height
    IPHONE_WIDTH = IPHONE_X_END - IPHONE_X_BEGIN
    IPHONE_HEIGHT = IPHONE_Y_END - IPHONE_Y_BEGIN

    logger.warning("Using AIR configuration with PLACEHOLDER iPhone dimensions. Update src/tinder_bot/scroll.py!")
    logger.info(f"Placeholder AIR dimensions: {IPHONE_WIDTH}x{IPHONE_HEIGHT}")
    logger.info(f"Placeholder AIR position: ({IPHONE_X_BEGIN}, {IPHONE_Y_BEGIN}) to ({IPHONE_X_END}, {IPHONE_Y_END})")
else:
    # Use system screen size for other environments
    SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()

# Set to True to enable debug mode with pauses for visual verification
DEBUG_MODE = os.getenv("DEBUG_SCROLL", "False").lower() == "true"


def get_hardcoded_window() -> Tuple[int, int, int, int]:
    """
    Return the hardcoded window dimensions based on the environment.
    
    Returns:
        Tuple[int, int, int, int]: (x, y, width, height) of the iPhone window
    """
    if ENVIRONMENT == "MONITOR":
        return (IPHONE_X_BEGIN, IPHONE_Y_BEGIN, IPHONE_WIDTH, IPHONE_HEIGHT)
    elif ENVIRONMENT == "PRO":
        return (IPHONE_X_BEGIN, IPHONE_Y_BEGIN, IPHONE_WIDTH, IPHONE_HEIGHT)
    elif ENVIRONMENT == "AIR":
        return (IPHONE_X_BEGIN, IPHONE_Y_BEGIN, IPHONE_WIDTH, IPHONE_HEIGHT)
    else:
        raise NotImplementedError(f"No hardcoded window dimensions for environment: {ENVIRONMENT}")


def get_safe_coordinates(x: int, y: int) -> Tuple[int, int]:
    """
    Ensure coordinates are within safe boundaries of the screen.
    
    Args:
        x: The x coordinate
        y: The y coordinate
        
    Returns:
        Tuple[int, int]: Safe coordinates within screen boundaries
    """
    # Define safe margins (50 pixels from edge)
    margin = 50
    
    # Ensure coordinates are within safe boundaries
    safe_x = max(margin, min(x, SCREEN_WIDTH - margin))
    safe_y = max(margin, min(y, SCREEN_HEIGHT - margin))
    
    # Log if coordinates were adjusted
    if safe_x != x or safe_y != y:
        logger.warning(f"Adjusted coordinates from ({x}, {y}) to safe values ({safe_x}, {safe_y})")
        print(f"WARNING: Coordinates ({x}, {y}) were outside safe screen boundaries.")
        print(f"Adjusted to ({safe_x}, {safe_y}) to prevent triggering PyAutoGUI fail-safe.")
    
    return safe_x, safe_y


def validate_bbox(bbox: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    """
    Validate and adjust the bounding box to fit within screen boundaries.
    
    Args:
        bbox: Original bounding box (x, y, width, height)
        
    Returns:
        Tuple[int, int, int, int]: Adjusted bounding box
    """
    # If ENVIRONMENT is defined, use hardcoded values
    if ENVIRONMENT == "MONITOR":
        logger.info("Using hardcoded MONITOR dimensions for iPhone window")
        return get_hardcoded_window()
    elif ENVIRONMENT == "PRO":
        logger.info("Using hardcoded PRO dimensions for iPhone window")
        return get_hardcoded_window()
    elif ENVIRONMENT == "AIR":
        logger.info("Using hardcoded AIR dimensions for iPhone window")
        return get_hardcoded_window()
    
    # Otherwise validate the provided bbox
    x, y, width, height = bbox
    
    # Check if the bbox is completely invalid (outside screen or zero dimensions)
    if width <= 0 or height <= 0 or x < 0 or y < 0 or x >= SCREEN_WIDTH or y >= SCREEN_HEIGHT:
        logger.warning(f"Invalid bbox detected: {bbox}")
        print(f"WARNING: Invalid window dimensions! Creating a default window.")
        
        # Create a new bbox with reasonable dimensions
        return get_hardcoded_window()
    
    return (x, y, width, height)


def wait_for_input(prompt="Press Enter to continue..."):
    """Wait for user input without requiring special privileges."""
    print(prompt)
    if DEBUG_MODE:
        input()  # Simple Enter key press
        print("Continuing...")


def move_to_iphone_center(bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """
    Move mouse pointer to the center of the iPhone window and return the coordinates.
    
    Args:
        bbox: Bounding box of iPhone window (x, y, width, height)
        
    Returns:
        Tuple[int, int]: The center (x, y) coordinates
    """
    # First validate and potentially fix the bbox
    bbox = validate_bbox(bbox)
    x, y, width, height = bbox
    
    # Calculate center coordinates of the window
    center_x = x + width // 2
    center_y = y + height // 2
    
    # Apply safety check to ensure coordinates are within screen bounds
    safe_x, safe_y = get_safe_coordinates(center_x, center_y)
    
    # Print debug info to console
    logger.info(f"Moving to iPhone center at: ({safe_x}, {safe_y})")
    
    # Move mouse to center of the window
    pyautogui.moveTo(safe_x, safe_y, duration=0.5)
    
    # If in debug mode, pause to allow visual verification
    if DEBUG_MODE:
        print("Mouse positioned at iPhone center. Please verify visually.")
        # wait_for_input("Press Enter to continue...")
    
    return safe_x, safe_y


def perform_stepped_scroll(amount: int) -> None:
    """
    Perform a scroll operation using multiple small steps for smoother scrolling.
    
    Args:
        amount: The total scroll amount (negative for down, positive for up)
    """
    # Calculate the small step size
    step_size = amount // STEPS_PER_SCROLL
    
    # Perform multiple small scrolls
    for _ in range(STEPS_PER_SCROLL):
        pyautogui.scroll(step_size)
        time.sleep(STEP_DELAY)  # Short delay between steps


def scroll_profile(bbox: Tuple[int, int, int, int]) -> None:
    """
    Scroll through a Tinder profile to reveal all photos and prompts.
    
    This function uses the exact scroll values for Tinder profiles:
    - First scroll: -660 pixels
    - Subsequent scrolls: -720 pixels
    - Total of 5 scrolls (resulting in 6 screenshots)
    - 2-second delay between scrolls
    
    Each scroll is broken into 10 smaller steps for smoother scrolling.
    
    Args:
        bbox: Bounding box of iPhone window (x, y, width, height)
    """
    # Move to center and get coordinates
    center_x, center_y = move_to_iphone_center(bbox)
    
    # Click to ensure focus
    logger.debug(f"Clicking at center point ({center_x}, {center_y}) to focus window")
    pyautogui.click()
    
    # Wait a moment before starting to scroll
    time.sleep(1.0)
    
    # If in debug mode, display test scrolls
    if DEBUG_MODE:
        print(f"DEBUG MODE: Testing scrolling with exact values")
        print(f"First scroll: {FIRST_SCROLL_AMOUNT}, Subsequent: {SUBSEQUENT_SCROLL_AMOUNT}")
        print(f"Taking {NUM_SCROLLS+1} screenshots (initial + {NUM_SCROLLS} scrolls)")
        print(f"Each scroll broken into {STEPS_PER_SCROLL} smaller steps")
    
    # First, perform the initial scroll with the specific value
    logger.info(f"Taking initial screenshot (before scrolling)")
    # This is where you would capture the first screenshot
    
    logger.info(f"First scroll: {FIRST_SCROLL_AMOUNT} pixels in {STEPS_PER_SCROLL} steps")
    pyautogui.click(center_x, center_y)
    time.sleep(0.1)
    perform_stepped_scroll(FIRST_SCROLL_AMOUNT)
    time.sleep(SCROLL_DELAY)
    logger.info(f"Taking screenshot #2 (after first scroll)")
    # This is where you would capture the second screenshot
    
    # Then, perform subsequent scrolls with their specific value
    for i in range(1, NUM_SCROLLS):
        logger.info(f"Scroll {i+1}/{NUM_SCROLLS}: {SUBSEQUENT_SCROLL_AMOUNT} pixels in {STEPS_PER_SCROLL} steps")
        
        # Click before each scroll to ensure window focus is maintained
        pyautogui.click(center_x, center_y)
        time.sleep(0.1)
        
        # Use the exact scroll amount with stepped scrolling
        perform_stepped_scroll(SUBSEQUENT_SCROLL_AMOUNT)
        
        # Use the exact 2-second delay between scrolls
        time.sleep(SCROLL_DELAY)
        
        logger.info(f"Taking screenshot #{i+3} (after scroll {i+1})")
        # This is where you would capture the screenshot
    
    # Brief pause at the end to ensure everything is loaded
    logger.info("Finished scrolling, pausing to ensure content is loaded")
    time.sleep(2.0)
    
    # Scroll back to top for next profile
    logger.info("Scrolling back to top of profile")
    # Calculate how many up-scrolls needed based on total distance scrolled
    total_scroll_distance = abs(FIRST_SCROLL_AMOUNT) + abs(SUBSEQUENT_SCROLL_AMOUNT) * (NUM_SCROLLS - 1)
    scrolls_needed = total_scroll_distance // abs(UP_SCROLL_AMOUNT) + 1
    
    for i in range(scrolls_needed):
        pyautogui.click(center_x, center_y)
        time.sleep(0.1)
        logger.debug(f"Scroll up {i+1}/{scrolls_needed}: {UP_SCROLL_AMOUNT} pixels in {STEPS_PER_SCROLL} steps")
        perform_stepped_scroll(UP_SCROLL_AMOUNT)
        time.sleep(0.5)
    
    logger.info("Profile scrolling complete - 6 screenshots should have been captured")