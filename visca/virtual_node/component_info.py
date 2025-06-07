from __future__ import annotations

import weakref
from enum import Enum
from typing import Optional


class ComponentType(Enum):
    CONTAINER = "Container"
    LIST = "List"
    COMPONENT = "Component"


class ComponentInfo:
    def __init__(
        self,
        node: 'VirtualNode',
        component_title: str='',
        component_context: str='',
        component_type: Optional[ComponentType]=None,
        component_code: Optional[str]=None,
        previously_seen: str=''
    ):
        self._node_ref = weakref.ref(node)
        self.component_title = component_title
        self.component_context = component_context
        self.component_type = component_type
        self.component_code = component_code
        self.previously_seen = previously_seen
    
    
    @property
    def node(self) -> Optional['VirtualNode']:
        """Safely access the associated VirtualNode."""
        return self._node_ref()
    
    
    def tabulate_code(self, code: str):
        return '\n'.join(
            list(map(
                lambda line: '\t' + line,
                code.split('\n')
            ))
        )
    
    
    def get_children_code(self):
        if self.component_type == ComponentType.CONTAINER:
            return self.tabulate_code(
                '\n'.join(
                    list(map(
                        lambda c: c.component_info.get_component_code(),
                        self.node.children
                    ))
                )
            )
        
        return self.tabulate_code(self.component_code)
    
    
    def get_component_code(self):
        title = self.component_title
        context = self.component_context.replace('"', '\\"')
        xpath = self.node.data.xpath
        x, y, width, height = self.node.data.get_bounding_box()
        
        component = 'ComponentList' if self.component_type == ComponentType.LIST \
            else self.component_type.value
        children = self.get_children_code()
        
        return f'<{component} name="{title}" context={{"{context}"}} xpath="{xpath}" x="{x}" y="{y}" width="{width}" height="{height}">\n{children}\n</{component}>'
