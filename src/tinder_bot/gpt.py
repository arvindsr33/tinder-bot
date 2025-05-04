"""GPT-4o integration for generating openers based on profile screenshots."""

from typing import List, Optional, Union, Tuple
import os
import openai
import logging
import base64
from pathlib import Path
import time
import re
from tinder_bot.system_prompt import opener_prompt, like_prompt, ad_check_prompt
from random import choice

# Import from our new image_utils module
from tinder_bot.image_utils import stitch_images, optimize_image

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_MODEL = "gpt-4.1"  # Default model to use
MAX_TOKENS = 400  # Increased to accommodate multiple openers
TEMPERATURE = 0.7  # Creativity level (0.0-1.0)

# User prompt focuses on the specific task and image description


FALLBACK_MESSAGE = "Hi there! I noticed something interesting in your profile, but I'd love to know more about you. What's been keeping you busy lately?"


def encode_image(image_path: str) -> str:
    """
    Encode an image file to a base64 string.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string of the image
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {e}")
        raise


def generate_opener(image_paths: Union[List[str], str]) -> Tuple[str, str]:
    """
    Generate a personalized opener based on profile screenshots.
    
    Args:
        image_paths: List of paths to profile screenshots or a single stitched image path
        
    Returns:
        Tuple containing the profile name and the full response
    """
    # Verify OpenAI API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable is not set")
        return "unknown", FALLBACK_MESSAGE
    
    # Get model from environment or use default
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    logger.info(f"Using OpenAI model: {model}")
    
    # Initialize OpenAI client
    client = openai.OpenAI(api_key=api_key)
    
    # Determine if we need to stitch images
    single_image_path = ""
    if isinstance(image_paths, str):
        # Single image (already stitched) provided
        single_image_path = image_paths
        logger.info(f"Using provided stitched image: {single_image_path}")
        is_stitched = True
    elif len(image_paths) > 1:
        # Stitch multiple images into one
        try:
            single_image_path = stitch_images(image_paths)
            logger.info(f"Created stitched image: {single_image_path}")
            is_stitched = True
        except Exception as e:
            logger.error(f"Failed to stitch images: {e}")
            # Fall back to using multiple images
            single_image_path = ""
            is_stitched = False
    else:
        is_stitched = False
    
    try:
        # Prepare the content for the API call
        content = []
        
        if single_image_path:
            # Process single stitched image
            logger.info(f"Processing stitched image: {single_image_path}")
            
            try:
                # Optimize image if needed
                optimized_path = optimize_image(single_image_path)
                
                # Encode the image
                base64_image = encode_image(optimized_path)
                
                # Add to content
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}",
                        "detail": "high"  # Use high detail for stitched image
                    }
                })
            except Exception as e:
                logger.error(f"Error processing stitched image {single_image_path}: {e}")
                return "unknown", FALLBACK_MESSAGE
        else:
            # Process and add each image separately
            for i, image_path in enumerate(image_paths):
                logger.info(f"Processing image {i+1}/{len(image_paths)}: {image_path}")
                
                try:
                    # Optimize image if needed
                    optimized_path = optimize_image(image_path)
                    
                    # Encode the image
                    base64_image = encode_image(optimized_path)
                    
                    # Add to content
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "low"  # Use "low" detail to reduce token usage
                        }
                    })
                except Exception as e:
                    logger.error(f"Error processing image {image_path}: {e}")
                    # Continue with remaining images
        
        # Call the OpenAI API
        logger.info("Sending request to OpenAI API")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": opener_prompt},
                {"role": "user", "content": content}
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE
        )
        
        # Extract the generated opener from the response
        full_response = response.choices[0].message.content.strip()
        logger.info(f"Generated full response: {full_response}")

        # Parse the response to extract the name
        name_match = re.search(r"Name: (.+)", full_response)
        name = name_match.group(1) if name_match else "unknown"

        return name, full_response
        
    except Exception as e:
        logger.error(f"Error generating opener: {e}")
        return "unknown", FALLBACK_MESSAGE 


def gpt_check_ads(image_path: str) -> str:
    """
    Calls OpenAI API to check if a single image screenshot is an advertisement.

    Args:
        image_path: Path to the single screenshot image.

    Returns:
        str: "YES" if it's an ad, "NO" otherwise (or fallback/error indicator).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable is not set for ad check")
        return "ERROR_API_KEY"

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL) 
    logger.info(f"Using OpenAI model for ad check: {model}")
    client = openai.OpenAI(api_key=api_key)

    try:
        # Optimize and encode the single image
        logger.info(f"Processing image for ad check: {image_path}")
        optimized_path = optimize_image(image_path)
        base64_image = encode_image(optimized_path)

        content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}",
                    "detail": "low" # Low detail might be sufficient for spotting an "AD" label
                }
            }
        ]

        # Call the OpenAI API with the ad_check_prompt
        logger.info("Sending ad check request to OpenAI API")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ad_check_prompt},
                {"role": "user", "content": content}
            ],
            max_tokens=5,  # Expecting only YES or NO
            temperature=0.1 # Very low temperature for deterministic check
        )

        decision = response.choices[0].message.content.strip().upper()
        logger.info(f"Received ad check decision from AI: {decision}")

        # Validate response
        if decision in ["YES", "NO"]:
            return decision
        else:
            logger.warning(f"Unexpected response format from ad check API: {decision}. Defaulting to NO.")
            return "NO" # Default to assuming it's not an ad if response is unclear

    except Exception as e:
        logger.error(f"Error during ad check API call: {e}", exc_info=True)
        return "ERROR_API_CALL"


def like_or_pass(stitched_image_path: str) -> Tuple[str, str]:
    """
    Calls OpenAI API to decide whether to LIKE or PASS a profile based on the image.
    Also retrieves the reason for the decision.

    Args:
        stitched_image_path: Path to the single stitched profile image.

    Returns:
        Tuple[str, str]: (Decision ("LIKE" or "PASS"), Reason string)
                           Returns ("LIKE", "AI response unparseable or refusal; defaulting to LIKE.") on failure.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable is not set")
        return "LIKE", "ERROR: API Key not set (Defaulting to LIKE)" # Default LIKE

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    logger.info(f"Using OpenAI model for like/pass: {model}")
    client = openai.OpenAI(api_key=api_key)
    full_response = "(No response received)" # Initialize in case of early error

    try:
        # Optimize and encode the single stitched image
        logger.info(f"Processing stitched image for like/pass: {stitched_image_path}")
        optimized_path = optimize_image(stitched_image_path)
        base64_image = encode_image(optimized_path)

        content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}",
                    "detail": "high" # Use high detail for decision making
                }
            }
        ]

        # Call the OpenAI API with the like_prompt
        logger.info("Sending like/pass request to OpenAI API")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": like_prompt},
                {"role": "user", "content": content}
            ],
            max_tokens=50,  # Increased slightly for reason
            temperature=0.2 # Low temperature for deterministic decision
        )

        full_response = response.choices[0].message.content.strip()
        logger.info(f"Received decision and reason from AI:\n{full_response}")
        # User requested print statement - keep it for now
        print(f"Received decision and reason from AI:\n{full_response}") 

        # Parse the response (expecting two lines)
        lines = full_response.split('\n')
        decision = "LIKE" # Default to LIKE on parsing failure
        reason = "Could not parse AI response."
        parsing_successful = False # Flag to track if parsing worked

        if len(lines) >= 2:
            decision_line = lines[0].strip().upper()
            reason_line = lines[1].strip()
            decision_parsed = False
            reason_parsed = False

            if decision_line.startswith("DECISION:"):
                extracted_decision = decision_line.split(":", 1)[-1].strip()
                if extracted_decision in ["LIKE", "PASS"]:
                    decision = extracted_decision
                    decision_parsed = True
                else:
                     logger.warning(f"Unexpected decision value: '{extracted_decision}'. Full response:\n{full_response}")
            else:
                 logger.warning(f"Decision line malformed: '{lines[0]}'. Full response:\n{full_response}")
            
            if reason_line.startswith("REASON:"):
                reason = reason_line.split(":", 1)[-1].strip()
                reason_parsed = True
            else:
                logger.warning(f"Reason line malformed: '{lines[1]}'. Full response:\n{full_response}")
                # Fallback: Use the second line as reason if first line was okay
                if decision_parsed: # Only if decision was parsed correctly
                   reason = reason_line # Assume the whole line is the reason
                   reason_parsed = True # Consider it parsed for the flag
            
            parsing_successful = decision_parsed and reason_parsed

        else: # len(lines) < 2
            logger.warning(f"Unexpected response format (expected 2 lines, got {len(lines)}). Full response:\n{full_response}")
            # Attempt to salvage decision if it's just one line
            if len(lines) == 1:
                 single_line = lines[0].strip().upper()
                 if single_line in ["LIKE", "PASS"]:
                     decision = single_line
                     reason = "(No reason provided by AI)"
                     parsing_successful = True # Salvaged decision
                 elif single_line.startswith("DECISION:"):
                      extracted_decision = single_line.split(":", 1)[-1].strip()
                      if extracted_decision in ["LIKE", "PASS"]:
                          decision = extracted_decision
                          reason = "(No reason provided by AI)"
                          parsing_successful = True # Salvaged decision

        # If parsing failed at any point, set the decision to LIKE and update reason
        if not parsing_successful:
             decision = "LIKE" # Default to LIKE on parsing failure/refusal
             reason = "AI response unparseable or refusal; defaulting to LIKE."
             # Log the failure
             logger.warning(f"AI response parsing failed. Defaulting to LIKE. Original full response:\n{full_response}")

        logger.info(f"Final Parsed Decision: {decision}, Reason: {reason}")
        return decision, reason

    except Exception as e:
        logger.error(f"Error during like/pass API call or parsing: {e}. Raw response:\n{full_response}", exc_info=True)
        # Default to LIKE on any exception during API call/parsing
        return "LIKE", f"Error during API call/parsing; defaulting to LIKE: {e}" 