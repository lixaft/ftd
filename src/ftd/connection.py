"""Connections related utilities."""
import logging

from maya import cmds, mel
from maya.api import OpenMaya

__all__ = ["find_related"]

LOG = logging.getLogger(__name__)


HISTORY = OpenMaya.MItDependencyGraph.kUpstream
FUTURE = OpenMaya.MItDependencyGraph.kDownstream


def invert(plug):
    """Inverse the given plug acording to its type.

    Schema:
        ┌──────────┐      ┌──────────┐
        │    +1    ■──────■    -1    │
        └──────────┘      └──────────┘

    Arguments:
        plug (str): The plug to invert.

    Returns:
        str: The inverted plug.

    Raises:
        TypeError: Invalid plug type.
    """
    plug_type = cmds.getAttr(plug, type=True)

    if plug_type == "matrix":
        node = cmds.createNode("inverseMatrix")
        cmds.connectAttr(plug, node + ".inputMatrix")
        return node + ".outputMatrix"

    if plug_type == "doubleLinear":
        mult = cmds.createNode("multDoubleLinear")
        cmds.setAttr(mult + ".input2", -1)
        cmds.connectAttr(plug, mult + ".input1")
        return mult + ".output"

    if plug_type == "doubleAngle":
        unit = cmds.createNode("unitConvertion")
        cmds.setAttr(unit + ".convertionFactor", -1)
        cmds.connectAttr(plug, unit + ".input")
        return unit + ".output"

    if plug_type == "double3":
        mult = cmds.createNode("multiplyDivide")
        cmds.setAttr(mult + ".input2", -1, -1, -1)
        for attribute in "XYZ":
            cmds.connectAttr(
                plug + attribute,
                "{}.input1{}".format(mult, attribute),
            )
        return mult

    msg = "The attribute type '%s' can't be inverted."
    raise TypeError(msg.format(plug_type))


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
    for attribute in (x + y for x in "srt" for y in "xyz"):
        cmds.connectAttr(
            "{}.o{}".format(decompose, attribute),
            "{}.{}".format(transform, attribute),
        )
    return decompose


def disconnect(plug):
    """Diconnect all the source connections from the given plug.

    In some case, a plug may have multiple source connections. In this
    situation, the last disconnected plug will be returned by the function.

    If the plug does have any source connection, return ``None``.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> a = cmds.createNode("transform", name="A")
        >>> b = cmds.createNode("transform", name="B")
        >>> _ = cmds.connectAttr(a + ".translateX", b + ".translateX")
        >>> disconnect(b + ".translateX")
        'A.translateX'

    Arguments:
        plug (str): The name of the plug to disconnect.

    Returns:
        str: The source name of the disconnected plug. If the given plug does
        not have any source connctions, return ``None``.
    """
    sources = cmds.listConnections(
        plug,
        source=True,
        destination=False,
        plugs=True,
    )
    source = (sources or [None])[0]
    if source:
        cmds.disconnectAttr(source, plug)
    return source


def find_related(root, node_type, stream=HISTORY):
    """Find a node related to the root.

    Arguments:
        root (str): The node from which the search will be based.
        node_type (str): The type of the node to find.
        stream (int): The direction in which the search will be performed.

    Returns:
        str: The name of the first node found. If no node matches the
            parameters, returns ``None``.
    """
    sel = OpenMaya.MSelectionList().add(root)
    mit = OpenMaya.MItDependencyGraph(
        sel.getDependNode(0),
        direction=stream,
        traversal=OpenMaya.MItDependencyGraph.kDepthFirst,
        level=OpenMaya.MItDependencyGraph.kPlugLevel,
    )
    while not mit.isDone():
        current = OpenMaya.MFnDependencyNode(mit.currentNode())
        # It would be better to use the maya function set constant directly
        # with the `filter` parameter. The problem is how to get this id from
        # the passed string? If anyone has an idea xD
        # e.g. mesh -> kMesh, skinCluster -> kSkinClusterFilter, etc.
        if current.typeName == node_type:
            return current.name()
        mit.next()
    return None


def next_available(plug, start=0):
    """Find the next available index of a multi attribute.

    Schema:
        ■ multi
        ├─■ multi[0]
        ├─■ multi[1]
        ├─■ ...

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> src = cmds.createNode("multMatrix", name="src")
        >>> dst = cmds.createNode("multMatrix", name="dst")
        >>> next_available(dst + ".matrixIn")
        'dst.matrixIn[0]'
        >>> _ = cmds.connectAttr(src + ".matrixSum", dst + ".matrixIn[0]")
        >>> next_available(dst + ".matrixIn")
        'dst.matrixIn[1]'

    Arguments:
        plug (str): The name of the multi attribute plug.
        start (int): The index from which the search should be start.

    Returns:
        str: The next available plug of the multi attribute.
    """
    index = mel.eval("getNextFreeMultiIndex {} {}".format(plug, start))
    return "{}[{}]".format(plug, index)
