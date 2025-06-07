from bs4 import BeautifulSoup, Tag, Comment


def clean_html(html, options=None):
    """
    Cleans HTML by removing unnecessary attributes and elements, and simplifying structure.
    
    Args:
        html (str or BeautifulSoup): HTML string or BeautifulSoup object to clean
        options (dict, optional): Configuration options.
            - essential_attributes: List of attributes to keep
            - unnecessary_tags: List of element tags to remove
            - generic_containers: List of elements considered generic containers
            
    Returns:
        BeautifulSoup: The cleaned BeautifulSoup object
    """
    # Default options
    default_options = {
        'essential_attributes': [
            'href', 'src', 'alt', 'title', 'name', 'value', 'type', 'for', 'action',
            'method', 'placeholder', 'checked', 'selected', 'disabled', 'readonly',
            'required', 'multiple', 'pattern', 'min', 'max', 'step', 'rows', 'cols'
        ],
        'unnecessary_tags': ['script', 'style', 'link', 'meta'],
        'generic_containers': ['div', 'span', 'section', 'article', 'main', 'aside']
    }
    
    # Merge provided options with defaults
    if options is None:
        options = {}
    
    merged_options = {
        'essential_attributes': options.get('essential_attributes', default_options['essential_attributes']),
        'unnecessary_tags': options.get('unnecessary_tags', default_options['unnecessary_tags']),
        'generic_containers': options.get('generic_containers', default_options['generic_containers'])
    }
    
    # Create BeautifulSoup object if input is string
    if isinstance(html, str):
        soup = BeautifulSoup(html, 'html.parser')
    else:
        soup = html
    
    # Clean the soup
    clean_element(soup, merged_options)
    
    return soup


def clean_element(element, options):
    """
    Recursively cleans an HTML element.
    
    Args:
        element (Tag): The BeautifulSoup tag to clean
        options (dict): Configuration options
    """
    # Skip if not a tag
    if not isinstance(element, Tag):
        return
    
    # 1. Remove unnecessary elements (comments, scripts, etc.)
    remove_unnecessary_elements(element, options['unnecessary_tags'])
    
    # 2. Remove unnecessary attributes
    remove_unnecessary_attributes(element, options['essential_attributes'])
    
    # 3. Process remaining children (bottom-up)
    for child in list(element.children):
        if isinstance(child, Tag):
            clean_element(child, options)

    # 4. Remove empty elements
    remove_empty_elements(element)
    
    # 5. Simplify the structure
    simplify_structure(element, options['generic_containers'])

    # 6. Remove empty elements
    remove_empty_elements(element)


def remove_unnecessary_elements(element, unnecessary_tags):
    """
    Removes unnecessary elements like comments, scripts, styles, etc.
    
    Args:
        element (Tag): The BeautifulSoup tag to process
        unnecessary_tags (list): Tags to remove
    """
    # Remove comments
    comments = element.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment.extract()
    
    # Remove unnecessary tags
    for tag_name in unnecessary_tags:
        for tag in element.find_all(tag_name):
            tag.decompose()


def remove_unnecessary_attributes(element, essential_attributes):
    """
    Removes unnecessary attributes like class, id, data-*, etc.
    
    Args:
        element (Tag): The BeautifulSoup tag to process
        essential_attributes (list): Attributes to keep
    """
    if not hasattr(element, 'attrs'):
        return
    
    # Get all attributes
    attrs_to_remove = []
    for attr in element.attrs:
        # Keep essential attributes and accessibility attributes
        if (attr not in essential_attributes and 
            # not attr.startswith('aria-') and 
            attr != 'role'):
            attrs_to_remove.append(attr)
    
    # Remove non-essential attributes
    for attr in attrs_to_remove:
        del element.attrs[attr]


def simplify_structure(element, generic_containers):
    """
    Recursively simplifies the structure by merging unnecessary nested containers.
    
    Args:
        element (Tag): The BeautifulSoup tag to process
        generic_containers (list): Elements considered generic containers
    """
    if not isinstance(element, Tag):
        return
    
    # Keep attempting to simplify until no more changes can be made
    changes_made = True
    while changes_made:
        changes_made = False
        
        # Get direct children that are tags
        child_elements = [child for child in element.children if isinstance(child, Tag)]
        
        # Process each child first (bottom-up approach)
        for child in child_elements:
            # Recursively simplify the child's structure first
            if simplify_structure(child, generic_containers):
                changes_made = True
        
        # After processing children, check if this element can be simplified
        if _can_merge_with_child(element, generic_containers):
            _merge_with_single_child(element)
            changes_made = True
    
    return changes_made


def _can_merge_with_child(element, generic_containers):
    """
    Checks if an element can be merged with its single child.
    
    Args:
        element (Tag): The BeautifulSoup tag to check
        generic_containers (list): Elements considered generic containers
        
    Returns:
        bool: True if mergeable, False otherwise
    """
    if not isinstance(element, Tag):
        return False
        
    # Get direct children that are tags
    child_elements = [child for child in element.children if isinstance(child, Tag)]
    
    # If element has exactly one child element
    if len(child_elements) == 1:
        child = child_elements[0]
        
        # Only consider merging if both parent and child are generic containers
        if (element.name in generic_containers and 
            child.name in generic_containers):
            
            # Get text content of parent and child
            parent_text = element.get_text(strip=True)
            child_text = child.get_text(strip=True)
            
            # If the parent's text equals the child's text, we can merge
            # This means there's no direct text in the parent that would be lost
            if parent_text == child_text:
                return True
    
    return False


def _merge_with_single_child(element):
    """
    Merges an element with its single child.
    
    Args:
        element (Tag): The BeautifulSoup tag to process
        generic_containers (list): Elements considered generic containers
    """
    child_elements = [child for child in element.children if isinstance(child, Tag)]
    
    if len(child_elements) == 1:
        child = child_elements[0]
        
        # Save all of the child's contents
        child_contents = list(child.contents)
        
        # Remove the child
        child.extract()
        
        # Add all of the child's contents back to the parent
        for content in child_contents:
            element.append(content)


def remove_empty_elements(element):
    """
    Recursively checks and removes elements that are empty.
    Preserves self-closing tags like img, input, br, hr, etc.
    
    Args:
        element (Tag): The BeautifulSoup tag to process
    """
    # List of self-closing tags that should never be removed even when empty
    self_closing_tags = ['img', 'input', 'br', 'hr', 'meta', 'link', 'source', 
                            'track', 'wbr', 'embed', 'param']
    
    if not isinstance(element, Tag):
        return
    
    # Process each child (need to convert to list since we'll modify the tree)
    children = list(element.find_all(recursive=False))
    for child in children:
        # Skip self-closing tags
        if child.name in self_closing_tags:
            continue
        
        # Process child's children first (bottom-up)
        remove_empty_elements(child)
    
    # Process this element's children again, as they may have changed
    children = list(element.find_all(recursive=False))
    for child in children:
        # Skip self-closing tags
        if child.name in self_closing_tags:
            continue
        
        # An element is considered empty if:
        # 1. It has no contents at all, or
        # 2. It only contains whitespace (after stripping)
        is_empty = False
        
        if len(child.contents) == 0:
            is_empty = True
        else:
            # Check if it only contains whitespace
            has_only_whitespace = True
            for content in child.contents:
                if isinstance(content, Tag):
                    has_only_whitespace = False
                    break
                elif str(content).strip():
                    has_only_whitespace = False
                    break
            
            if has_only_whitespace:
                is_empty = True
        
        # Remove if empty
        if is_empty:
            child.decompose()
