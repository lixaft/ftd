# coding: utf-8
"""Provide utilities related to the outliner."""
import logging

from maya import cmds

LOG = logging.getLogger(__name__)


def sort(root=None, recursive=False):
    """Sort the children of the provided root.

    root:    ──────>   root:
     └── C              └── A
      ── A               ── B
      ── B               ── C

    If no root node is specified, reorder the top level nodes.

    Arguments:
        root (str): The node from which their children will be sorted.
        recursive (bool): Recurssively sort all descendants of the root.
    """
    if root is None:
        nodes = cmds.ls(assemblies=True)
    else:
        nodes = cmds.listRelatives(root, children=True) or []
    for child in reversed(sorted(nodes)):
        cmds.reorder(child, front=True)
        if recursive:
            sort(child, recursive=True)
