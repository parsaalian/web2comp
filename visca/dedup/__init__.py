import numpy as np
from PIL import Image

from visca.virtual_node import build_dom_tree
from .hash import (
    compute_image_hashes,
    remove_hash_duplicates
)
from .padding import (
    process_padding_duplicates
)


def load_image_arrays(segments):
    """Load images as numpy arrays for direct comparison."""
    image_arrays = {}
    for segment in segments:
        try:
            image = Image.open(segment['screenshot'])
            image_arrays[segment['xpath']] = np.array(image)
        except Exception as e:
            print(f"Error loading {segment['screenshot']}: {e}")
            image_arrays[segment['xpath']] = None
    return image_arrays


def deduplicate_screenshots(
    segments,
    allowed_deviation=0.075,
):
    """
    Deduplicate HTML screenshots based on hashes and padding analysis.
    
    The algorithm is:
    1. Remove exact hash duplicates first
    2. For remaining parent-child pairs (where parent has only one child),
        check if parent is child with added padding
    
    Args:
        segments: The list containing the segments from the segmentation
        allowed_deviation: Maximum percentage of outlier padding pixels allowed (0.0-1.0)
    """
    # Get all valid segments
    all_segments = [s for s in segments if s['xpath'].startswith("//html") and s['screenshot'] != '']
    
    if not all_segments:
        print("No segments files found in results.")
    
    # Precompute image hashes
    print(f"Computing image hashes for {len(all_segments)} segments...")
    image_hashes = compute_image_hashes(segments)
    
    # First pass: remove exact hash duplicates
    hash_duplicates = remove_hash_duplicates(segments, image_hashes)
    print(f"Found {len(hash_duplicates)} exact hash duplicates")
    
    # Remaining segments after hash deduplication
    remaining_segments = [s for s in all_segments if s['xpath'] not in hash_duplicates]
    
    # Second pass: check for padding duplicates (if enabled)
    padding_duplicates = set()
    
    # Load image arrays for direct pixel comparison
    image_arrays = load_image_arrays(remaining_segments)
    
    # Build the DOM tree from remaining files
    dom_tree = build_dom_tree(remaining_segments)
    
    # Process the tree to find padding duplicates
    padding_duplicates = process_padding_duplicates(
        dom_tree, image_arrays, allowed_deviation
    )
    print(f"Found {len(padding_duplicates)} padding duplicates")
    
    # Combine all duplicates
    all_duplicates = hash_duplicates | padding_duplicates
    
    print(f"Removing {len(all_duplicates)} duplicate screenshots...")
    remaining_segments = [s for s in all_segments if s['xpath'] not in all_duplicates]
    
    files_kept = len(all_segments) - len(all_duplicates)
    print(f"Deduplication complete. Kept {files_kept} of {len(all_segments)} segments.")

    return remaining_segments


__all__ = [
    'deduplicate_screenshots'
]
