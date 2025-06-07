from typing import Optional, List

from visca.segment import Segment

from .virtual_node_data import VirtualNodeData
from .component_info import ComponentInfo, ComponentType
from .diff_info import DiffInfo, DiffType


class VirtualNode:
    def __init__(self, data: Segment):
        # print(data.get('xpath', ''), data.get('screenshot', ''))
        self.data = VirtualNodeData(data)
        
        # --- Tree Structure (initialized empty, populated during tree building) ---
        self.parent: Optional['VirtualNode'] = None
        # Children list preserves insertion order
        self.children: List['VirtualNode'] = []
        
        self.component_info: Optional[ComponentInfo] = None
        self.diff_info: Optional[DiffInfo] = None

        # Algorithmic Fields
        self.psi = 0.0        
        self.is_instance = False
    
    
    def add_child(self, child_node: 'VirtualNode'):
        """
        Adds a child node to this node's children list (preserving order)
        and sets the child's parent reference.
        """
        if not isinstance(child_node, VirtualNode):
            raise TypeError("Child must be an instance of VirtualNode.")
        # Check if this exact child instance is already present
        if child_node not in self.children:
            self.children.append(child_node) # Append preserves insertion order
        child_node.parent = self # Set parent reference
    
    
    def add_component_info(
        self,
        component_title: str='',
        component_context: str='',
        component_type: Optional[ComponentType]=None,
        component_code: Optional[str]=None,
        previously_seen: str=''
    ):
        if self.component_info is None:
            self.component_info = ComponentInfo(self)
        
        if component_title != '':
            self.component_info.component_title = component_title
        if component_context != '':
            self.component_info.component_context = component_context
        if component_type is not None:
            self.component_info.component_type = component_type
        if component_code is not None:
            self.component_info.component_code = component_code
        if previously_seen != '':
            self.component_info.previously_seen = previously_seen
    
    
    def add_diff_info(self, diff_type: Optional[DiffType]=None):
        self.diff_info = DiffInfo(diff_type=diff_type)


    def shallow_copy(self) -> 'VirtualNode':
        '''
        Copies all the VirtualNode's data except for the children.
        '''
        copied_node = VirtualNode(dict(self.data._raw_data))
        
        if self.component_info is not None:
            copied_node.add_component_info(
                component_title=self.component_info.component_title,
                component_type=self.component_info.component_type,
                component_code=self.component_info.component_code
            )
        
        if self.diff_info is not None:
            copied_node.add_diff_info(
                diff_type=self.diff_info.diff_type
            )
        
        return copied_node
    
    
    def full_copy(self) -> 'VirtualNode':
        '''
        Copies VirtualNode's data including its children.
        '''
        copied_node = self.shallow_copy()
        
        for child in self.children:
            copied_child = child.full_copy()
            copied_node.add_child(copied_child)
        
        return copied_node

    @property
    def tag(self) -> str:
        """
        Expose tag name expected by the segmentation algorithm."""
        return self.data.tag_name           

    @property
    def xpath(self) -> str:
        """Expose absolute XPath expected by the segmentation algorithm."""
        return self.data.xpath