"""Provide utilities for tasks unrelated to maya."""
import logging

from maya import cmds

LOG = logging.getLogger(__name__)

__all__ = ["is_visible"]


def is_visible(node):
    """Check if the node is visible by querying all its ancestors.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> a = cmds.createNode("transform", name="A")
        >>> b = cmds.createNode("transform", name="B", parent=a)
        >>> cmds.setAttr(a + ".visibility", False)
        >>> cmds.getAttr(b + ".visibility")
        True
        >>> is_visible(b)
        False

    Arguments:
        node (str): The node to check.

    Returns:
        bool: True if the node is visible, False otherwise.
    """
    path = cmds.ls(node, long=True)[0]
    while "|" in path:
        path, tail = path.rsplit("|", 1)
        visible = cmds.getAttr(tail + ".visibility")
        if not visible:
            return False
    return True
