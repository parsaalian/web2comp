import re
import hashlib
from typing import List, Dict, Set
import json
from pathlib import Path

import imagehash
from PIL import Image

from visca.virtual_node import (
    VirtualNode,
    ComponentType
)
from visca.html_processing import clean_html


def hash_string(string: str) -> str:
    '''
    Hashes a string using SHA-256.
    '''
    return hashlib.sha256(string.encode()).hexdigest()


def compute_image_hash(image_path):
    image = Image.open(image_path)
    return imagehash.phash(image)


def extract_response_from_tag(llm_output, tag_name):
    match = re.search(rf"<{tag_name}>(.*?)</{tag_name}>", llm_output, re.DOTALL)
    
    if match:
        response_content = match.group(1).strip()
        return response_content if response_content else None
    else:
        return None


def _get_ancestor_context(node: VirtualNode):
    contexts: List[str] = []
    parent = node.parent

    while parent is not None and parent.data.tag_name != "root":
        
        # Guard for Ancestors that have not been classifed yet
        title = (
            parent.component_info.component_title          # may raise
            if getattr(parent, "component_info", None)     # guard first
            else None
        )
        if title:
            contexts.append(title)
        parent = parent.parent

    return list(reversed(contexts))

def collect_parent_nodes(
    root: "VirtualNode",
    targets: Set[str],
    found: Dict[str, "VirtualNode"],
):
    """
    Depth-first walk that stops as soon as we've located *all* XPaths in
    `targets`.  Nothing is classified here.
    """
    stack = [root]
    counter = 0
    while stack and targets:
        node = stack.pop()
        counter += 1
        xp = node.data.xpath
        if xp in targets:                 # parent segment hit!
            found[xp] = node
            found[xp].add_component_info(
                component_type=ComponentType.CONTAINER
            )
            targets.remove(xp)
        # else:
        #     stack.extend(node.children)   
        stack.extend(node.children)
    
    print(f"Nodes Traversed: {counter}")


def classify_and_describe_candidates(
    root: VirtualNode,
    classification_model,
    page_context,
    memory: dict,
    segment_json_path: str | Path,
):
    #  Logging
    run_log: dict = {
        "meta": {},
        "nodes": {}
    }

    # 1 ─ Load parent-segment XPaths
    with open(segment_json_path, "r") as f:
        segment_info = json.load(f)
    container_xpaths: Set[str] = set(segment_info.keys())
    print(f"▶ Loaded {len(container_xpaths)} parent segments")
    run_log["meta"]["loaded_parents"] = len(container_xpaths)

    # 2 ─ Locate those nodes (single DOM traversal, no LLM calls)
    found: Dict[str, VirtualNode] = {}
    collect_parent_nodes(root, set(container_xpaths), found)
    print(f"▶ Found {len(found)}/{len(container_xpaths)} parent nodes in DOM")
    run_log["meta"]["found_nodes"] = len(found)
  
    queue: List[VirtualNode] = list(found.values()) 
    
    while len(queue) > 0:
        node = queue[0]

        # print(node.data.xpath)
        
        while True:
            try:
                # node_id = hash_string(clean_html(node.data.raw_html).prettify())
                node_id = compute_image_hash(node.data.screenshot)
                ancestor_ctx = "\n".join(_get_ancestor_context(node))
                
                if node_id not in memory:
                    response_full = classification_model(
                        file=node.data.screenshot,
                        prompt = f"Page Context: {page_context}\n"
                                 f"Ancestors:\n{ancestor_ctx}"
                    )
                    response = response_full.text

                    if not isinstance(response, str) or not response.strip():
                        print(response_full)
                        # Something went wrong upstream → log & treat as “unknown component”
                        print("⚠️  empty or non-string response for", node.data.xpath)
                        print(node.data.screenshot)
                        print(f"Page Context: {page_context}\n"
                                 f"Ancestors:\n{ancestor_ctx}")
                        
                        
                    component_type = extract_response_from_tag(response, 'Classification')
                    component_context = extract_response_from_tag(response, 'Context')
                    component_title = extract_response_from_tag(response, 'Title')
                    node.add_component_info(
                        component_type=ComponentType(component_type),
                        component_title=component_title,
                        component_context=component_context
                    )
                    
                    print(node.data.xpath, node_id, component_type, component_title)
                else:
                    component_type = memory[node_id]['type']
                    component_context = memory[node_id]['context']
                    component_title = memory[node_id]['title']
                    previously_seen = memory[node_id]['original_state']
                    node.add_component_info(
                        component_type=component_type,
                        component_title=component_title,
                        component_context=component_context,
                        previously_seen=previously_seen
                    )
                    
                    print('IN MEMORY', node.data.xpath, node_id, component_type, component_title)
                
                run_log["nodes"][node.data.xpath] = {
                    "node_id"       : str(node_id),
                    "component_type": node.component_info.component_type.name,
                    "component_title": node.component_info.component_title,
                    "source"        : "memory" if node_id in memory else "model"
                }

                
                if node.component_info.component_type == ComponentType.CONTAINER:
                    queue.extend(node.children)
                
                break
            except Exception as e:
                print(str(e))
        
        queue = queue[1:]
    
    return root, run_log


def transform_candidate(
    root: VirtualNode,
    component_generation_model,
    page_context: str,
    memory: dict,
    state_id: str
):
    queue: List[VirtualNode] = [root]
    
    while len(queue) > 0:
        node = queue[0]
        
        if node.data.tag_name == 'root':
            queue.extend(node.children)
            queue = queue[1:]
            continue

        ancestor_ctx = "\n".join(_get_ancestor_context(node))
        prompt = f"""Page Context: {page_context}
                    Ancestors:
                    {ancestor_ctx}
                    Raw HTML:
                    {node.data.raw_html}"""
        
        while True:
            try:
                # node_id = hash_string(clean_html(node.data.raw_html).prettify())
                node_id = compute_image_hash(node.data.screenshot)
                
                if node_id in memory and 'code' in memory[node_id] and memory[node_id]['code'] != '':
                    node.add_component_info(
                        component_code=memory[node_id]['code']
                    )
                    
                    print('IN MEMORY', node.data.xpath, node_id)
                    
                    if node.component_info.component_type == ComponentType.CONTAINER:
                        queue.extend(node.children)
                else:
                    if node.component_info.component_type == ComponentType.CONTAINER:
                        queue.extend(node.children)
                    else:
                        element_class = 'SegmentIsListOfItems' if node.component_info.component_type == ComponentType.LIST else 'SegmentIsSingularComponent'
                        component = extract_response_from_tag(
                            component_generation_model(
                                file=node.data.screenshot,
                                prompt=f'Class: {element_class}\n{prompt}'
                            ).text.replace('```jsx', '').replace('```', ''),
                            'JsxOutput'
                        )
                        node.add_component_info(component_code=component)
                    
                    memory[node_id] = {
                        'type': node.component_info.component_type,
                        'title': node.component_info.component_title,
                        'context': node.component_info.component_context,
                        'code': node.component_info.component_code,
                        'original_state': state_id
                    }
                
                    print(node.data.xpath, node_id)
                
                break
            except Exception as e:
                print(str(e))
        
        queue = queue[1:]
    
    return memory, root
