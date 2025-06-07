from __future__ import annotations
from collections import Counter
from typing import Dict

# Structural Helpers
def tag_multiset(node: "VirtualNode", depth: int = 3) -> Counter[str]:
    """Return a *multiset* of tag names in *node*'s subtree.

    Only the first ``depth`` levels are considered (``depth`` ≤ 0 stops
    the recursion).  The result is a :class:`collections.Counter`, so
    union/intersection operations are cheap.
    """
    if depth == 0:
        return Counter()

    sig: Counter[str] = Counter([node.tag])
    for child in node.children:
        sig += tag_multiset(child, depth - 1)
    return sig


def jaccard_distance(a: "VirtualNode", b: "VirtualNode") -> float:
    """Cheap structural Jaccard distance in the interval [0, 1]."""
    sa, sb = tag_multiset(a), tag_multiset(b)
    inter = sum((sa & sb).values())
    union = sum((sa | sb).values())
    return 1.0 - (inter / union) if union else 0.0


def subtree_size(node: "VirtualNode") -> int:
    """Count *all* nodes in the subtree rooted at *node*, including itself."""
    return 1 + sum(subtree_size(ch) for ch in node.children)

# PSI Scorers
def _psi_vs_children(node: "VirtualNode", psi_children: float, sibling_score: float) -> float:
    """Internal helper: compute this node's PSI given pre‑computed values."""
    return subtree_size(node) / (1.0 + sibling_score)


def calculate_psi_avg(node: "VirtualNode") -> float:
    """Compute PSI where the denominator uses the **average** sibling distance.

    A post‑order traversal labels each node in‑place:
    ``node.is_instance`` ⇒ whether *node* is the chosen component root; and
    ``node.psi`` ⇒ the winning PSI value for the entire subtree.
    """
    # ――― recurse first ―――
    child_psis = [calculate_psi_avg(ch) for ch in node.children]
    psi_children = 1.0
    for v in child_psis:
        psi_children *= v

    # ――― local sibling average ―――
    if node.parent is None:
        sibling_avg = 0.0
    else:
        siblings = [sib for sib in node.parent.children if sib is not node]
        sibling_avg = (
            sum(jaccard_distance(node, sib) for sib in siblings) / len(siblings)
            if siblings
            else 0.0
        )

    psi_root = _psi_vs_children(node, psi_children, sibling_avg)

    # ――― choose winner ―――
    if psi_root >= psi_children:
        node.psi = psi_root
        node.is_instance = True
        return psi_root
    else:
        node.psi = psi_children
        node.is_instance = False
        return psi_children


def calculate_psi_sum(node: "VirtualNode") -> float:
    """Compute PSI where the denominator uses the **sum** of sibling distances."""
    # ――― recurse first ―――
    if not node.children:          # <-- NEW
        node.psi = 1.0
        node.is_instance = True
        return 1.0
    child_psis = [calculate_psi_sum(ch) for ch in node.children]
    psi_children = 1.0
    for v in child_psis:
        psi_children *= v

    # ――― sum of sibling distances ―――
    if node.parent is None:
        sibling_sum = 0.0
    else:
        sibling_sum = sum(
            jaccard_distance(node, sib) for sib in node.parent.children if sib is not node
        )

    psi_root = _psi_vs_children(node, psi_children, sibling_sum)

    # ――― choose winner ―――
    if psi_root >= psi_children:
        node.psi = psi_root
        node.is_instance = True
        return psi_root
    else:
        node.psi = psi_children
        node.is_instance = False
        return psi_children

# Utility Helpers
def gather_instances(root: "VirtualNode") -> Dict[str, int]:
    """Return a ``{xpath: size}`` mapping for all nodes flagged as instances."""
    instances: Dict[str, int] = {}

    def walk(n: "VirtualNode") -> None:  # inner helper to capture *instances* dict
        if getattr(n, "is_instance", False):
            instances[n.xpath] = subtree_size(n)
        else:
            for ch in n.children:
                walk(ch)

    walk(root)
    return instances


def ascii_tree(node: "VirtualNode", indent: str = "", is_last: bool = True) -> str:
    """Return an ASCII rendition of the subtree with PSI annotations."""
    branch = "└── " if is_last else "├── "
    psi = getattr(node, "psi", 0.0)
    star = " *" if getattr(node, "is_instance", False) else ""
    line = f"{indent}{branch}{node.tag}  ψ={psi:.2f}{star}\n"
    indent_child = indent + ("    " if is_last else "│   ")
    for i, ch in enumerate(node.children):
        line += ascii_tree(ch, indent_child, i == len(node.children) - 1)
    return line
