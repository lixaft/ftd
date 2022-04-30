"""Provide utilities related to offsets."""
import logging
import math

from maya import cmds
from maya.api import OpenMaya

import ftd.attribute
import ftd.connection

__all__ = [
    "group",
    "inverse_group",
    "matrix",
    "matrix_to_group",
    "reset_matrix",
    "unmatrix",
]

LOG = logging.getLogger(__name__)


def group(node, suffix="offset"):
    """Create a group above the node with the same transformation values.

    Arguments:
        node (str): The node which create the offset group.
        suffix (str): The suffix of the offset group.

    Returns:
        str: The offset node name.
    """
    offset = cmds.createNode(
        "transform",
        name="{}_{}".format(node, suffix),
        parent=(cmds.listRelatives(node, parent=True) or [None])[0],
    )
    cmds.matchTransform(offset, node)
    cmds.parent(node, offset)
    return offset


def inverse_group(node):
    """Create an offset that cancel the transformation values of the nodes.

    Arguments:
        node (str): The node which create the inverse offset.

    Returns:s
        str: The offset node name.
    """
    inverse = group(node, suffix="inverse")
    offset = group(inverse)
    offset = cmds.rename(offset, node + "_offset")
    ftd.graph.matrix_to_srt(node + ".inverseMatrix", inverse)
    return offset


def matrix(node):
    """Transfer the transformation to the offsetParentMatrix attribute.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> node = cmds.createNode("transform")
        >>> cmds.setAttr(node + ".translateY", 5)
        >>> matrix(node)
        >>> cmds.getAttr(node + ".translateY")
        0.0
        >>> cmds.getAttr(node + ".offsetParentMatrix")[-3]
        5.0

    Arguments:
        node (str): The name of the node to offset.
    """
    matrix_ = OpenMaya.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))
    parent = OpenMaya.MMatrix(cmds.getAttr(node + ".parentInverseMatrix[0]"))
    cmds.setAttr(node + ".offsetParentMatrix", matrix_ * parent, type="matrix")
    ftd.attribute.reset(node, ftd.attribute.SRT)


def matrix_to_group():
    """Converts all uses of offsetParentMatrix plug to a `traditional` offset.

    This plug is great but can cause some problems as it is not taken into
    account when exporting caches like alembics.

    If the plug has a value that is not equal to an identity matrix, add an
    offset to the node. If the plug has a source connection, add an offset to
    the node, decompose the matrix and plug the result into the offset node.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> offset = cmds.createNode("transform")
        >>> node = cmds.createNode("transform", parent=offset)
        >>> cmds.setAttr(offset + ".translate", 10, 2, 5)
        >>> _ = cmds.connectAttr(
        ...     node + ".inverseMatrix",
        ...     offset + ".offsetParentMatrix"
        ... )
        >>> matrix_to_group()
    """
    for plug in cmds.ls("*.offsetParentMatrix"):
        sources = cmds.listConnections(plug, source=True, plugs=True)
        node = plug.split(".", 1)[0]

        if sources:
            source = (sources or [None])[0]
            cmds.disconnectAttr(source, plug)
            unmatrix(node)
            ftd.connection.matrix_to_srt(source, group(node))

        elif OpenMaya.MMatrix(cmds.getAttr(plug)) != OpenMaya.MMatrix():
            unmatrix(node)
            group(node)


def reset_matrix(node):
    """Reset the offsetParentMatrix attribute to identity.

    Arguments:
        node (str): The node to reset.
    """
    matrix_ = OpenMaya.MMatrix()
    cmds.setAttr(node + ".offsetParentMatrix", matrix_, type="matrix")


def unmatrix(node):
    """Transfer the transformation to the translate/rotate/scale attributes.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> from maya.api import OpenMaya
        >>> node = cmds.createNode("transform")
        >>> matrix = OpenMaya.MMatrix()
        >>> matrix[-3] = 5
        >>> cmds.setAttr(node + ".offsetParentMatrix", matrix, type="matrix")
        >>> unmatrix(node)
        >>> cmds.getAttr(node + ".translateY")
        5.0

    Arguments:
        node (str): The target node.
    """
    matrix_ = OpenMaya.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))
    tmatrix = OpenMaya.MTransformationMatrix(matrix_)
    space = OpenMaya.MSpace.kTransform

    with ftd.attribute.unlock(node):
        cmds.setAttr(node + ".translate", *tmatrix.translation(space))
        cmds.setAttr(node + ".rotate", *map(math.degrees, tmatrix.rotation()))
        cmds.setAttr(node + ".scale", *tmatrix.scale(space))
        reset_matrix(node)
