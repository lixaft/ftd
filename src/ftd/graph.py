"""Provide utilities related to the node graph."""
import contextlib
import logging

from maya import cmds, mel
from maya.api import OpenMaya

import ftd.attribute

__all__ = [
    "delete_unused",
    "find_related",
    "lock_node_editor",
    "matrix_to_srt",
]

LOG = logging.getLogger(__name__)


def delete_unused():
    """Delete all the unused nodes in the scene."""
    mel.eval("MLdeleteUnused")


def find_related(root, type, direction="up"):
    # pylint: disable=redefined-builtin
    """Find a node related to the root.

    The following are the valid value for ``type`` parameter:

    ======== ===========================
     Value         Description
    ======== ===========================
    ``up``   From destination to source.
    ``down`` From source to destination.
    ``dn``   Alias of ``down``.
    ======== ===========================

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> mesh = cmds.polyCube()[0]
        >>> shape = cmds.listRelatives(mesh, shapes=True)[0]
        >>> _ = cmds.cluster(mesh)
        >>> find_related(shape, type="cluster")
        'cluster1'

    Arguments:
        root (str): The node name from which the search should start.
        type (str): The type of node to be searched.
        direction (str): Should be search in up or down stream?

    Returns:
        str: The name of the first node found. If no node matches the
            parameters, returns "None".

    Raises:
        ValueError: The value of the direction is not covered by this function.
            Please refer to the documentation to see all valid values.
    """
    if direction in ("up",):
        direction = OpenMaya.MItDependencyGraph.kUpstream
    elif direction in ("dn", "down"):
        direction = OpenMaya.MItDependencyGraph.kDownstream
    else:
        msg = "Invalid direction value: '{}'.".format(direction)
        LOG.error(msg)
        raise ValueError(msg)

    sel = OpenMaya.MSelectionList().add(root)
    mit = OpenMaya.MItDependencyGraph(
        sel.getDependNode(0),
        direction=direction,
        traversal=OpenMaya.MItDependencyGraph.kDepthFirst,
        level=OpenMaya.MItDependencyGraph.kPlugLevel,
    )
    while not mit.isDone():
        current = OpenMaya.MFnDependencyNode(mit.currentNode())
        # It would be better to use the maya function set constant directly
        # with the `filter` parameter. The problem is how to get this id from
        # the passed string? If anyone has an idea xD
        # e.g. mesh -> kMesh, skinCluster -> kSkinClusterFilter, etc.
        if current.typeName == type:
            return current.name()
        mit.next()
    return None


@contextlib.contextmanager
def lock_node_editor():
    """Prevents adding new nodes in the Node Editor.

    This context manager can be useful when building rigs as adding nodes to
    the editor at creation can be very time consuming when many nodes are
    generated at the same time.
    """
    panel = mel.eval("getCurrentNodeEditor")
    state = cmds.nodeEditor(panel, query=True, addNewNodes=True)
    cmds.nodeEditor(panel, edit=True, addNewNodes=False)
    yield
    cmds.nodeEditor(panel, edit=True, addNewNodes=state)


def matrix_to_srt(plug, transform):
    """Connect a matrix plug to scale/rotate/translate attributes.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> node = cmds.createNode("transform")
        >>> mult = cmds.createNode("multMatrix")
        >>> matrix_to_srt(mult + ".matrixSum", node)
        'multMatrix1_decomposeMatrix'

    Arguments:
        plug (str): The matrix plud to decompose.
        transform (str): The name of the transform that recieve the matrix.

    Returns:
        str: The name of the decomposeMatrix node use.
    """
    name = plug.split(".", 1)[0] + "_decomposeMatrix"
    decompose = cmds.createNode("decomposeMatrix", name=name)
    cmds.connectAttr(plug, decompose + ".inputMatrix")
    for attribute in ftd.attribute.SRT:
        cmds.connectAttr(
            "{}.o{}".format(decompose, attribute),
            "{}.{}".format(transform, attribute),
        )
    return decompose
