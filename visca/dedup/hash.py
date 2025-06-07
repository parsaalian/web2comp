from collections import defaultdict

import imagehash
from PIL import Image


def compute_image_hashes(segments):
    """Compute perceptual hashes for all image files."""
    image_hashes = {}
    for segment in segments:
        try:
            image = Image.open(segment['screenshot'])
            image_hashes[segment['xpath']] = imagehash.phash(image)
        except Exception as e:
            print(f"Error processing {segment['screenshot']}: {e}")
            image_hashes[segment['xpath']] = None
    return image_hashes


def are_images_identical(hash1, hash2, threshold=0):
    """Compare two image hashes to determine if they are identical."""
    if hash1 is None or hash2 is None:
        return False
    return hash1 - hash2 <= threshold


def are_images_similar(hash1, hash2, threshold=5):
    """Compare two image hashes to determine if they are similar."""
    if hash1 is None or hash2 is None:
        return False
    return hash1 - hash2 < threshold


def remove_hash_duplicates(segments, image_hashes):
    """First pass: remove exact hash duplicates."""
    to_remove = set()
    hash_to_segments = defaultdict(list)
    
    for segment in segments:
        hash_val = image_hashes.get(segment['xpath'])
        if hash_val is not None:
            hash_to_segments[hash_val].append(segment)
    
    for _, segments in hash_to_segments.items():
        if len(segments) > 1:
            segments.sort(key=lambda s: len(s['xpath']))
            to_remove.update(
                list(map(lambda s: s['xpath'], segments[1:]))
            )
    
    return to_remove
