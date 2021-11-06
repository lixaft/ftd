"""This module provides utilities for common tasks involving curves."""
import logging

from maya import cmds

import ftd.name

__all__ = ["cvs_position", "from_transform"]

LOG = logging.getLogger(__name__)


def cvs_position(node, world=False):
    """Query the position of each control points of a curve.

    Examples:
        >>> from maya import cmds
        >>> node = cmds.curve(
        ...     point=[(-5, 0, 0), (0, 5, 0), (5, 0, 0)],
        ...     degree=1,
        ... )
        >>> cmds.setAttr(node + ".translateZ", -2)
        >>> cvs_position(node, world=True)
        [(-5.0, 0.0, -2.0), (0.0, 5.0, -2.0), (5.0, 0.0, -2.0)]

    Arguments:
        node (str): The curve node to query.
        world (bool): Specify on which space the coordinates will be returned.

    Returns:
        list: A two-dimensional array that contains all the positions of the
        points that compose the curve.
    """
    pos = cmds.xform(
        node + ".cv[*]",
        query=True,
        translation=True,
        worldSpace=world,
        absolute=world,
    )
    # build an array with each point position in it's own array.
    return [tuple(pos[x * 3 : x * 3 + 3]) for x, _ in enumerate(pos[::3])]


def from_transform(nodes, name="curve", degree=3, close=False, attach=False):
    """Create a curve with each point at the position of a transform node.

    If the "attachment" parameter is set to "True", each cvs of the created
    curve will be driven by the node that gave it its position.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> a = cmds.createNode("transform")
        >>> b = cmds.createNode("transform")
        >>> c = cmds.createNode("transform")
        >>> cmds.setAttr(b + ".translate", 5, 10, 0)
        >>> cmds.setAttr(c + ".translate", 10, 0, 0)
        >>> from_transform((a, b, c), degree=1)
        'curve'

    Arguments:
        nodes (list): The transformation nodes to use as position.
        name (str): The name of the curve.
        degree (int): The degree of the curve.
        close (bool): Specifies if the curve is closed or not.
        attach (bool): Constrains the position of cvs at nodes.

    Returns:
        str: The curve name.
    """
    flags = {"query": True, "translation": True, "worldSpace": True}
    point = [cmds.xform(x, **flags) for x in nodes]

    flags = {}
    if close:
        point.extend(point[:degree])
        flags["periodic"] = True
        flags["knot"] = range(len(point) + degree - 1)

    name = ftd.name.generate_unique(name)
    curve = cmds.curve(point=point, degree=degree, **flags)
    curve = cmds.rename(curve, name)
    if not attach:
        return curve

    for index, node in enumerate(nodes):
        name = node + "_decomposeMatrix"
        decompose = cmds.createNode("decomposeMatrix", name=name)
        cmds.connectAttr(node + ".worldMatrix[0]", decompose + ".inputMatrix")
        cmds.connectAttr(
            decompose + ".outputTranslate",
            "{}.cv[{}]".format(curve, index),
        )

    return curve
