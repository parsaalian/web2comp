import numpy as np

from visca.virtual_node import VirtualNode


def analyze_image_flatness(image, bin_size=1):
    """
    Analyze image flatness by finding the dominant color and 
    calculating the percentage of pixels that are not that color.
    
    Args:
        image: numpy array with shape (height, width, 3)
        bin_size: Size of color bins (1 for exact, higher for more tolerance)
        
    Returns:
        Dictionary with flatness metrics
    """
    total_pixels = len(image)
    
    # Bin colors if needed (for handling similar colors)
    if bin_size > 1:
        binned_image = (image // bin_size) * bin_size
    else:
        binned_image = image
    
    # Convert RGB values to a single integer for faster processing
    r, g, b = binned_image[:,0], binned_image[:,1], binned_image[:,2]
    color_integers = (r.astype(np.int64) * 256 * 256 + 
                        g.astype(np.int64) * 256 + 
                        b.astype(np.int64)).flatten()
    
    # Find unique colors and their counts
    unique_integers, counts = np.unique(color_integers, return_counts=True)
    
    # Find the dominant color
    dominant_idx = np.argmax(counts)
    dominant_integer = unique_integers[dominant_idx]
    dominant_count = counts[dominant_idx]
    
    # Convert dominant color integer back to RGB
    r_dom = (dominant_integer // (256*256)) % 256
    g_dom = (dominant_integer // 256) % 256
    b_dom = dominant_integer % 256
    dominant_color = (int(r_dom), int(g_dom), int(b_dom))
    
    # Calculate percentage of non-dominant pixels
    non_dominant_count = total_pixels - dominant_count
    non_dominant_percentage = non_dominant_count / total_pixels
    
    return {
        'dominant_color': dominant_color,
        'dominant_percentage': dominant_count / total_pixels,
        'non_dominant_percentage': non_dominant_percentage
    }


def is_padding_duplicate(parent_array, child_array, allowed_deviation=0.075):
    """
    Check if parent is the same as child but with added padding.
    
    Algorithm:
    1. Check if child dimensions are smaller than parent
    2. Try to find child as a subarray within parent
    3. If found, check if padding pixels are roughly the same color (with tolerances)
    
    Args:
        parent_array: Numpy array of parent image
        child_array: Numpy array of child image
        color_threshold: Maximum color distance allowed between padding pixels
        allowed_deviation: Maximum percentage of outlier padding pixels allowed
        debug: Whether to print debugging information
    
    Returns:
        tuple: (is_duplicate, offset_x, offset_y) or (False, None, None)
    """
    if parent_array is None or child_array is None:
        return False, None, None
    
    # Get dimensions
    parent_h, parent_w = parent_array.shape[:2]
    child_h, child_w = child_array.shape[:2]
    
    # Child must be smaller than parent
    if child_h > parent_h or child_w > parent_w:
        return False, None, None
    
    # Calculate all possible positions to check
    max_x = parent_w - child_w + 1
    max_y = parent_h - child_h + 1
    
    # Try all possible positions
    for start_y in range(max_y):
        for start_x in range(max_x):
            # Extract region from parent
            region = parent_array[start_y:start_y+child_h, start_x:start_x+child_w]
            
            # Check if region matches child (with exact match first for efficiency)
            if np.array_equal(region, child_array):
                # Create a mask where True = child area, False = padding
                mask = np.zeros((parent_h, parent_w), dtype=bool)
                mask[start_y:start_y+child_h, start_x:start_x+child_w] = True
                
                # Extract all padding pixels
                padding_pixels = parent_array[~mask]
                
                # Skip if no padding (shouldn't happen but just in case)
                if padding_pixels.size == 0:
                    continue
                
                flatness = analyze_image_flatness(padding_pixels)
                
                if flatness['non_dominant_percentage'] < allowed_deviation:
                    return True
    
    return False


def process_padding_duplicates(
    node: VirtualNode,
    image_arrays,
    allowed_deviation=0.075,
    visited=None
):
    """
    Second pass: check for padding duplicates in parent-child relationships.
    Only process nodes with exactly one child.
    
    Args:
        node: The DOM node to process
        image_arrays: Dictionary of image arrays
        allowed_deviation: Maximum percentage of outlier padding pixels allowed
        visited: Set of already visited nodes
    
    Returns:
        set: Segments to remove due to padding duplication
    """
    if visited is None:
        visited = set()
    
    # Skip if already visited to avoid cycles
    node_path = node.data.xpath if hasattr(node, 'xpath') else str(id(node))
    if node_path in visited:
        return set()
    visited.add(node_path)
    
    to_remove = set()
    
    # Process all children first (bottom-up approach)
    for child in node.children:
        to_remove.update(process_padding_duplicates(
            child, image_arrays, allowed_deviation, visited
        ))
    
    # Skip root node
    if node.data.tag_name == "root":
        return to_remove
    
    # Only process nodes with exactly one child
    if len(node.children) == 1:
        child = node.children[0]
        parent_array = image_arrays.get(node.data.xpath)
        child_array = image_arrays.get(child.data.xpath)
        
        # Check if parent contains child with single-color padding
        is_padding = is_padding_duplicate(parent_array, child_array, allowed_deviation)
        
        if is_padding:
            to_remove.add(child.data.xpath)
    
    return to_remove
