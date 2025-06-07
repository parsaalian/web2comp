from typing import List, Dict

from visca.segment import Segment

from .virtual_node import VirtualNode
from .diff_info import DiffType
from .utils import calculate_parent_xpath


def parse_xpath(xpath: str) -> List[str]:
    """
    Parses an XPath into a list of its segments.
    Example: /html[1]/body[1] -> ['/html[1]', '/html[1]/body[1]']
             //div[1]/span[1] -> ['//div[1]', '//div[1]/span[1]']
    """
    if not xpath:
        return []

    # Handle // prefix carefully
    prefix = ""
    path_to_split = xpath
    if xpath.startswith("//"):
        prefix = "//"
        path_to_split = xpath[2:]
    elif xpath.startswith("/"):
        prefix = "/"
        path_to_split = xpath[1:]

    segments = [part for part in path_to_split.split('/') if part]

    # Reconstruct full path segments
    full_path_segments = []
    for i, segment in enumerate(segments):
        if i == 0 and prefix in ["/", "//"]:
            full_path_segments.append(prefix + segment)
        elif i > 0 :
            current_path = full_path_segments[-1] + "/" + segment
            full_path_segments.append(current_path)
        else:
            full_path_segments.append(segment)

    return full_path_segments


def build_dom_tree(segments: List[Segment]) -> VirtualNode:
    """
    Build a DOM tree of VirtualNode objects from a list of segments using
    a trie-like approach based on XPath prefixes. Does not create placeholder
    nodes. Preserves child insertion order relative to their parent.

    Args:
        segments: A list of dictionaries, each representing a node with
                    at least 'xpath' and 'tag' keys, plus other attributes.

    Returns:
        The artificial root node of the constructed tree.
    """
    # Create an artificial root node for the whole tree
    root = VirtualNode({'tag': 'root', 'xpath': '', 'id': 'ARTIFICIAL_ROOT', 'index': -1})
    # Dictionary to quickly find nodes by their exact XPath
    nodes_by_xpath: Dict[str, VirtualNode] = {'': root}

    # Sort segments by XPath length first, then based in index provided in the segment.
    # This heuristic increases the likelihood of processing parents before children.
    segments.sort(key=lambda s: s['index'])

    for segment_data in segments:
        xpath = segment_data.get('xpath')
        if not xpath:
            print(f"Warning: Segment data missing 'xpath'. Skipping: {segment_data.get('tag', 'N/A')}")
            continue

        # Check if this exact node already exists (duplicate segment)
        if xpath in nodes_by_xpath:
            print(f"Warning: Node with XPath '{xpath}' already exists. Skipping duplicate segment for tag '{segment_data.get('tag')}'.")
            # Optionally update existing node data here if needed
            # existing_node = nodes_by_xpath[xpath]
            # Update logic... e.g., merge attributes, update text if empty?
            continue

        parent_node = None
        # Start searching from the direct parent XPath
        current_search_xpath = calculate_parent_xpath(xpath)

        while current_search_xpath is not None:
            if current_search_xpath in nodes_by_xpath:
                # Found the deepest existing ancestor node
                parent_node = nodes_by_xpath[current_search_xpath]
                break # Exit the while loop
            # If not found, go up one level
            current_search_xpath = calculate_parent_xpath(current_search_xpath)

        # If no parent found other than root (current_search_xpath becomes None),
        # the parent is the root node. This should be caught by `nodes_by_xpath['']`.
        if parent_node is None:
            # This case should theoretically only happen if root wasn't added to nodes_by_xpath
            # Or if calculate_parent_xpath has issues. Assume root is the fallback.
            print(f"Warning: Could not find existing parent for XPath '{xpath}'. Attaching to root.")
            parent_node = root

        try:
            new_node = VirtualNode(segment_data)
            parent_node.add_child(new_node) # Adds to children list, sets parent reference
            nodes_by_xpath[xpath] = new_node # Add new node to lookup map
        except (TypeError, ValueError) as e:
            print(f"Error creating VirtualNode for XPath '{xpath}': {e}. Skipping segment.")

    return root


def diff_bfs_update(root: VirtualNode, diff_type: DiffType) -> VirtualNode:
    queue = [root]
    
    while len(queue) > 0:
        current_node = queue[0]
        current_node.add_diff_info(diff_type=diff_type)
        queue.extend(current_node.children)
        queue = queue[1:]
    
    return root


def build_diff_tree(left_tree: VirtualNode, right_tree: VirtualNode) -> VirtualNode:
    new_tree = left_tree.shallow_copy()
    new_tree.add_diff_info(DiffType.SAME)
    
    left_children: List[VirtualNode] = left_tree.children
    right_children: List[VirtualNode] = right_tree.children

    left_pointer = 0
    right_pointer = 0
    
    # If left_children is empty, all of right_tree nodes are added nodes.
    if len(left_children) == 0 and len(right_children) != 0:
        for right_child in right_children:
            new_child = right_child.full_copy()
            new_child = diff_bfs_update(new_child, DiffType.ADDED)
            new_tree.add_child(new_child)
            new_tree.add_diff_info(diff_type=DiffType.UPDATED)
            return new_tree
    
    while left_pointer < len(left_children):
        left_child = left_children[left_pointer]
        right_child = right_children[right_pointer]
        
        if left_child.data == right_child.data or \
            left_child.data.is_similar(right_child.data):
            
            new_child = build_diff_tree(left_child, right_child)
            new_tree.add_child(new_child)
            
            if new_child.diff_info.diff_type != DiffType.SAME and left_child.data != right_child.data:
                new_tree.add_diff_info(diff_type=DiffType.UPDATED)
            
            left_pointer += 1
            # Here, the match is found and the rest of the body is unnecessary.
            right_pointer = (right_pointer + 1) % len(right_children)
            continue
        
        new_child = right_child.full_copy()
        new_child = diff_bfs_update(new_child, DiffType.ADDED)
        new_tree.add_child(new_child)
        new_tree.add_diff_info(diff_type=DiffType.UPDATED)
        
        right_pointer += 1
        
        # If we have compared the self_child to all the other_children and not found a match
        # This means that self_child has been removed from the list.
        if right_pointer == len(right_children):
            new_child = left_child.full_copy()
            new_child = diff_bfs_update(new_child, DiffType.DELETED)
            new_tree.add_child(new_child)
            new_tree.add_diff_info(diff_type=DiffType.UPDATED)
            
            left_pointer += 1
            right_pointer = 0
    
    return new_tree


def print_diff_tree(root: VirtualNode):
    queue = [root]
    
    while len(queue) > 0:
        current = queue[0]
        queue.extend(current.children)
        
        if current.diff_info.diff_type == DiffType.SAME:
            queue = queue[1:]
            continue
        
        print(current.data.xpath, current.diff_info.diff_type.value)
        print(current.data.raw_html)
        
        queue = queue[1:]
