import re
from typing import Optional, Dict, Any, Tuple

from visca.segment import Segment


class VirtualNodeData:
    """
    Represents the data for a dom node.
    """

    def __init__(self, data: Segment):
        """
        Initializes a VirtualNodeData from a dictionary containing its properties.

        Args:
            data: A dictionary expected to contain keys like 'tag', 'xpath',
                    'text', 'html', 'x', 'y', 'width', 'height', 'visible',
                    'index', 'screenshot', and potentially 'id'.
        """
        if not isinstance(data, dict):
            raise TypeError("Input 'data' must be a dictionary.")
        # XPath is essential for building/lookup, Tag is essential for representation
        # Allow empty xpath only for the conceptual root
        if 'xpath' not in data and data.get('tag') != 'root':
            raise ValueError("Input 'data' must contain an 'xpath' key.")
        if 'tag' not in data:
            raise ValueError("Input 'data' must contain a 'tag' key.")

        # Core Identification and Structure
        self.node_id: Optional[str] = data.get('id')
        self.tag_name: str = data['tag']
        # Use get for xpath to handle the root node case where it might be '' or None initially
        self.xpath: str = data.get('xpath', '')
        self.index: Optional[int] = data.get('index') # Positional index from source list

        # Content
        self.text_content: str = data.get('text', '')
        self.raw_html: str = data.get('html', '') # Raw HTML snippet for this node

        # Positional/Visual Attributes (Common in segmentation outputs)
        self.x: int = data.get('x', 0)
        self.y: int = data.get('y', 0)
        self.width: int = data.get('width', 0)
        self.height: int = data.get('height', 0)
        self.visible: bool = data.get('visible', True)
        self.screenshot: Optional[str] = data.get('screenshot') # Path to image segment

        # Store the original data for potential future reference or debugging
        self._raw_data: Dict[str, Any] = data
        # Placeholder for standard HTML attributes if parsed later
        self.attributes: Dict[str, str] = self._parse_attributes_from_html(self.raw_html)


    def _parse_attributes_from_html(self, html_snippet: Optional[str]) -> Dict[str, str]:
        """
        Basic parsing of attributes from the opening tag of the raw HTML snippet.
        Note: This is a simple parser and might not handle all edge cases perfectly.
        """
        attributes = {}
        if not html_snippet:
            return attributes
        # Regex updated to handle self-closing tags slightly better and find first tag
        # Make tag matching case-insensitive in regex
        match = re.search(r"<" + re.escape(self.tag_name) + r"(\s+[^>]*)?>", html_snippet, re.IGNORECASE | re.DOTALL)
        if match:
            attr_string = match.group(1) if match.group(1) else ''
            # Regex updated to handle boolean attributes (where =value is optional)
            # It matches the key, and then optionally matches the = sign and value part.
            attr_pattern = re.compile(r'\s+([\w\-:]+)(?:\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s/>"]+)))?', re.IGNORECASE)
            for attr_match in attr_pattern.finditer(attr_string):
                key = attr_match.group(1)
                # Check if the value part matched (groups 2, 3, 4)
                value = attr_match.group(2) # Double quotes
                if value is None:
                    value = attr_match.group(3) # Single quotes
                if value is None:
                    value = attr_match.group(4) # No quotes

                # If value is still None after checking groups 2, 3, 4,
                # it means the optional (=value) part didn't match.
                # This indicates a boolean attribute. Assign empty string.
                if value is None:
                    value = ""

                attributes[key.lower()] = value # Store keys in lowercase for consistency
        return attributes


    @property
    def depth(self) -> int:
        """
        Estimates the depth of the node in the tree based on the number of
        tag segments in its XPath. Adjusts for potential leading '//' or '/'.
        Depth of root ('') is 0. Depth of '/html[1]' is 1.
        """
        normalized_xpath = self.xpath
        if not normalized_xpath: # Root node
            return 0

        # Remove potential leading '//' or start count after first '/' for absolute paths
        if normalized_xpath.startswith("//"):
            # Depth for //tag is usually considered context-dependent, treat as 1 for simplicity?
            normalized_xpath = normalized_xpath[2:]
            if not normalized_xpath:
                return 1 # Just '//' is unlikely
        elif normalized_xpath.startswith("/"):
            normalized_xpath = normalized_xpath[1:] # Remove leading '/' before counting segments
            if not normalized_xpath:
                return 0 # Just '/' - unlikely XPath

        # Count the '/' characters which separate segments
        # Add 1 because N separators mean N+1 segments (e.g., 'a/b' has 1 separator, 2 segments)
        # If there are no separators (like 'html[1]'), count is 0, so return 1.
        return normalized_xpath.count('/') + 1


    def get_bounding_box(self) -> Optional[Tuple[int, int, int, int]]:
        """Returns the bounding box as a tuple (x, y, width, height) if available."""
        if self.x is not None and self.y is not None and self.width is not None and self.height is not None:
            return (self.x, self.y, self.width, self.height)
        return None


    def is_similar(self, other: 'VirtualNodeData'):
        return self.tag_name == other.tag_name and \
                self.xpath == other.xpath


    def __eq__(self, other: 'VirtualNodeData'):
        return self.tag_name == other.tag_name and \
                self.xpath == other.xpath and \
                self.text_content == other.text_content and \
                self.x == other.x and \
                self.y == other.y and \
                self.width == other.width and \
                self.height == other.height and \
                self.visible == other.visible


    def __repr__(self) -> str:
        """Provides an unambiguous representation of the node."""
        return f"<VirtualNodeData tag='{self.tag_name}' xpath='{self.xpath}'>"


    def __str__(self) -> str:
        """Provides a simple string representation, often the tag name."""
        return self.tag_name
