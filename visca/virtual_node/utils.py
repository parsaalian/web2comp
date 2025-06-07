from typing import Optional


def calculate_parent_xpath(xpath: str) -> Optional[str]:
    """
    Calculates the XPath of the potential parent node by removing the
    last segment of the given XPath. Returns None if no parent segment exists.
    Static method as it doesn't depend on instance state.
    """
    if not xpath or '/' not in xpath:
        # If xpath is empty, '', or just 'tag[1]', no parent path separator exists
        return None

    # Use rsplit to remove the last segment
    parent_path = xpath.rsplit('/', 1)[0]

    # If the original path was like '/html[1]' rsplit gives '', which means parent is root (represented by '')
    # If original was '//div[1]/span[1]' rsplit gives '//div[1]'
    if parent_path == "" and xpath.startswith('/'): # e.g. /html[1] -> parent is conceptual root ''
        return '' # Return empty string for the root's parent XPath
    elif parent_path == "" and not xpath.startswith('/'):
        # e.g., html[1]/body[1] -> parent is html[1] (this case shouldn't happen with abs paths)
        # Or //a -> parent_path is '', needs careful handling based on XPath source meaning.
        # Assuming standard absolute paths, this case might indicate root or error.
        return None # Treat as error/unknown for non-absolute paths without '/'
    elif parent_path in ["/", "//"] and xpath.startswith("//"): # Handle case like //div -> parent is //
        # The conceptual parent of '//tag' is often considered the document root.
        # Representing the document root consistently (e.g., with '') is better.
        return '' # Map parent of top-level absolute search to root ''

    return parent_path
