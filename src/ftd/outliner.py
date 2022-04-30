# coding: utf-8
"""Provide utilities related to the outliner."""
import logging

from maya import cmds
from maya.api import OpenMaya

LOG = logging.getLogger(__name__)


def sort(root=None, recursive=False):
    """Sort the children of the provided root.

    Schema:
        root:    ──────>   root:
        ├─■ C              ├─■ A
        ├─■ A              ├─■ B
        └─■ B              └─■ C

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


def makedirs(path, node="transform"):
    """Create a full path in maya outliner.

    Schema:
        root:
        └─■ A
          └─■ B
            └─■ C

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> makedirs("A|B|C")
        'C'
        >>> cmds.listRelatives("C", parent=True)[0]
        'B'
        >>> cmds.listRelatives("B", parent=True)[0]
        'A'

    Arguments:
        path (str): The full path to create.
        node (str): The type of node to create for the path.

    Returns:
        str: The name of the tail of the path.
    """
    tail = None
    for each in path.split("|"):
        if not cmds.objExists(each):
            tail = cmds.createNode(node, name=each, parent=tail)
    return tail


def iter_descendants(node, path=False):
    """Safe iteration over the descendants of the given node.

    Arguments:
        node (str): The name of the root node.
        path (bool): Return the full path instead of just the node name.

    Yeilds:
        str: The current node name or path.
    """
    sel = OpenMaya.MSelectionList()
    sel.add(node)
    obj = sel.getDependNode(0)
    iterator = OpenMaya.MItDag()
    iterator.reset(obj)
    iterator.next()
    while not iterator.isDone():
        if path:
            yield iterator.fullPathName()
        else:
            yield iterator.partialPathName()
        iterator.next()
