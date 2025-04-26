"""Utility functions for image processing and manipulation."""

from typing import List, Optional, Tuple
import os
import time
import logging
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

def stitch_images(image_paths: List[str], 
                 output_dir: Optional[str] = None,
                 delete_originals: bool = False,
                 layout: Optional[Tuple[int, int]] = None) -> str:
    """
    Stitch multiple screenshots into a single image in a grid layout.
    
    Args:
        image_paths: List of paths to the screenshots to stitch
        output_dir: Directory to save the stitched image (defaults to ./screenshots/stitched)
        delete_originals: Whether to delete the original images after stitching
        layout: Optional tuple of (rows, cols) for custom grid layout. 
               Defaults to (2, 3) for backward compatibility.
        
    Returns:
        Path to the stitched image file
    """
    if len(image_paths) < 1:
        logger.error("No images provided for stitching")
        raise ValueError("At least one image is required for stitching")
    
    # Sort images by their index in the filename if available
    def extract_index(path):
        try:
            # Extract number from filename (e.g., profile_screenshot_2_...)
            filename = os.path.basename(path)
            parts = filename.split('_')
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
        except:
            pass
        return 999  # Default high value for files without proper numbering
        
    sorted_paths = sorted(image_paths, key=extract_index)
    num_images = len(sorted_paths)
    
    logger.info(f"Stitching {num_images} images...")
    
    # Determine grid layout
    if layout:
        rows, cols = layout
        if rows * cols < num_images:
            logger.warning(
                f"Provided layout ({rows}x{cols}) cannot fit all {num_images} images. "
                f"Some images will be omitted."
            )
    else:
        # Default 2x3 layout for backward compatibility
        if num_images <= 3:
            cols = num_images
            rows = 1
        else:
            cols = 3
            rows = 2
    
    # Load all images
    try:
        images = [Image.open(path) for path in sorted_paths]
    except Exception as e:
        logger.error(f"Error loading images: {e}")
        raise
    
    # Ensure all images have the same dimensions
    width, height = images[0].size
    for i, img in enumerate(images):
        if img.size != (width, height):
            logger.warning(f"Image {i+1} has different dimensions. Resizing to match first image.")
            images[i] = img.resize((width, height), Image.LANCZOS)
    
    # Create a new image with grid layout
    grid_width = width * cols
    grid_height = height * rows
    stitched_img = Image.new('RGB', (grid_width, grid_height))
    
    # Paste images in grid
    for i, img in enumerate(images):
        if i >= cols * rows:
            logger.warning(f"Too many images ({num_images}), only using first {cols * rows}")
            break
            
        row = i // cols
        col = i % cols
        x = col * width
        y = row * height
        stitched_img.paste(img, (x, y))
    
    # Generate directory name based on date
    date_str = time.strftime("%Y%m%d")
    profile_dir = Path(f"./screenshots/profile_{date_str}")
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp for unique filename
    timestamp = time.strftime("%H%M%S")
    stitched_path = profile_dir / f"profile_stitched_{timestamp}.png"
    
    # Save the stitched image
    try:
        stitched_img.save(stitched_path, format="PNG", dpi=(300, 300))
        logger.info(f"Stitched image saved to: {stitched_path}")
    except Exception as e:
        logger.error(f"Error saving stitched image: {e}")
        raise
    
    # Delete original images if requested
    if delete_originals:
        for path in sorted_paths:
            try:
                os.remove(path)
                logger.debug(f"Deleted original image: {os.path.basename(path)}")
            except Exception as e:
                logger.warning(f"Could not delete {path}: {e}")
    
    return str(stitched_path)

def optimize_image(image_path: str, max_size_mb: float = 5.0) -> str:
    """
    Optimize an image to reduce its size if needed.
    
    Args:
        image_path: Path to the image file
        max_size_mb: Maximum size in MB
        
    Returns:
        Path to the optimized image (same as input if no optimization needed)
    """
    # Check current file size
    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
    
    # If file is already small enough, return the original path
    if file_size_mb <= max_size_mb:
        return image_path
    
    logger.info(f"Image {image_path} is {file_size_mb:.2f}MB, optimizing to under {max_size_mb}MB")
    
    # Open and resize the image
    img = Image.open(image_path)
    
    # Calculate scaling factor based on current size
    scale_factor = (max_size_mb / file_size_mb) ** 0.5
    new_width = int(img.width * scale_factor)
    new_height = int(img.height * scale_factor)
    
    # Resize the image
    resized_img = img.resize((new_width, new_height), Image.LANCZOS)
    
    # Prepare new filename
    path = Path(image_path)
    new_path = path.parent / f"{path.stem}_optimized{path.suffix}"
    
    # Save with optimization
    resized_img.save(new_path, optimize=True, quality=85)
    
    logger.info(f"Optimized image saved to {new_path}")
    return str(new_path) 