"""Message input module for sending openers in Tinder chats."""

import pyautogui
import time
import random
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Constants
MAX_MESSAGE_LENGTH = 200  # Maximum message length (per requirements)
TYPING_SPEED_MIN = 0.01  # Minimum delay between characters for human-like typing
TYPING_SPEED_MAX = 0.03  # Maximum delay


def send_opener(opener: str, bbox: Tuple[int, int, int, int]) -> None:
    """
    Send an opener message in the Tinder chat.
    
    Args:
        opener: Generated opener text
        bbox: Bounding box of iPhone window (x, y, width, height)
    """
    if not opener:
        logger.error("Empty message provided, cannot send")
        return
    
    # Truncate message if too long
    if len(opener) > MAX_MESSAGE_LENGTH:
        logger.warning(f"Message exceeds {MAX_MESSAGE_LENGTH} characters, truncating")
        opener = opener[:MAX_MESSAGE_LENGTH - 3] + "..."
    
    logger.info(f"Sending opener: {opener}")
    
    x, y, width, height = bbox
    
    # Based on the screenshot, the text input area is at the very bottom of the screen
    # Calculate position of the text input field - approximately 90% down from the top
    input_x = x + width // 2
    input_y = y + int(height * 0.9)  # Text input is near the bottom
    
    # Click on the text input field
    logger.debug(f"Clicking on text input at ({input_x}, {input_y})")
    pyautogui.click(input_x, input_y)
    
    # Wait a moment before typing
    time.sleep(random.uniform(0.5, 1.0))
    
    # Type the message (with human-like timing)
    logger.debug("Typing opener message")
    pyautogui.typewrite(opener)
    
    # Wait a moment after typing
    time.sleep(random.uniform(0.5, 1.0))
    
    # Find and click the send button (usually to the right of the text field)
    # In Tinder, this might be at the right edge of the text input area
    send_button_x = x + width - 40  # 40 pixels from right edge
    send_button_y = input_y  # Same vertical position as the text input
    
    logger.debug(f"Clicking send button at ({send_button_x}, {send_button_y})")
    pyautogui.click(send_button_x, send_button_y) 