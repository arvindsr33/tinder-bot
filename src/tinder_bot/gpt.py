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


def like_or_pass(stitched_image_path: str) -> str:
    """
    Calls OpenAI API to decide whether to LIKE or PASS a profile based on the image.

    Args:
        stitched_image_path: Path to the single stitched profile image.

    Returns:
        str: "LIKE" or "PASS" (or fallback/error indicator)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable is not set")
        return "ERROR_API_KEY"

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    logger.info(f"Using OpenAI model for like/pass: {model}")
    client = openai.OpenAI(api_key=api_key)

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
            max_tokens=10,  # Expecting only LIKE or PASS
            temperature=0.2 # Low temperature for deterministic decision
        )

        decision = response.choices[0].message.content.strip().upper()
        logger.info(f"Received decision from AI: {decision}")

        # Validate response
        if decision in ["LIKE", "PASS"]:
            return decision
        else:
            logger.warning(f"Unexpected response format from like/pass API: {decision}")
            return choice(["LIKE", "PASS"])

    except Exception as e:
        logger.error(f"Error during like/pass API call: {e}", exc_info=True)
        return "ERROR_API_CALL" 