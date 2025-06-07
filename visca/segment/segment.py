from typing import Optional, TypedDict


class Segment(TypedDict):
    id: Optional[str]
    tag: str
    xpath: str
    text: str
    html: str
    x: int
    y: int
    width: int
    height: int
    visible: bool
    index: int
    screenshot: str
