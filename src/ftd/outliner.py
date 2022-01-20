"""Provide utilities related to the outliner."""
import logging

from maya import cmds

LOG = logging.getLogger(__name__)


def sort_children(root, recursive=False):
    """Sort the children of the provided root.

    Arguments:
        root (str): The node from which their children will be sorted.
        recursive (bool): Sort recursively.
    """
    children = cmds.listRelatives(root, children=True) or []
    for child in reversed(sorted(children)):
        cmds.reorder(child, front=True)
        if recursive:
            sort_children(child, recursive=True)
