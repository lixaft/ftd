"""Provide utilities related to constraints."""
import itertools
import logging

from maya import cmds
from maya.api import OpenMaya

__all__ = ["matrix"]

LOG = logging.getLogger(__name__)


def matrix(driver, driven, offset=False, srt="srt"):
    """Constraint two node using matrix nodes.

    Examples:
        >>> from maya import cmds
        >>> a = cmds.polyCube(name="A")[0]
        >>> b = cmds.polyCube(name="B")[0]
        >>> cmds.setAttr(b + ".translateX", 10)
        >>> matrix(a, b, offset=True)
        'B_multMatrix'

    Arguments:
        driver (str): The plug or the node that will be drive the constraint.
        driven (str): The node that will be drived by the constraint.
        offset (bool): Maintain the offset between the driver and the driven.
        srt (str): The attribute to connect to the driven node.

    Returns:
        str: The name of the `multMatrix` node used for the constraint.

    Raises:
        ValueError: The driver is not a matrix plug or a transform node.
    """
    # Parse and check the parameters to find the node/plug to use
    if "." in driver:
        if cmds.getAttr(driver, type=True) != "matrix":
            raise ValueError("The plug '{}' is not a matrix.".format(driver))
        driver_plug = driver
    elif "transform" in cmds.nodeType(driver, inherited=True):
        driver_plug = driver + ".worldMatrix[0]"
    else:
        raise ValueError("Invalid driver parameter: '{}'.".format(driver))

    if "transform" not in cmds.nodeType(driven, inherited=True):
        raise ValueError("Invalid driven parameter: '{}'.".format(driven))

    # Alias parameter for consistency
    driven_plug = driven + ".worldMatrix[0]"

    # Create the node that will process the matrix calculation
    mult = cmds.createNode("multMatrix", name=driven + "_multMatrix")

    # Initialize an iterator to get the index to use on the multMatrix input
    index = itertools.count(0)

    # Find the offset between the driver and the driven nodes
    if offset:
        driver_matrix = OpenMaya.MMatrix(cmds.getAttr(driver_plug))
        driven_matrix = OpenMaya.MMatrix(cmds.getAttr(driven_plug))
        cmds.setAttr(
            "{}.matrixIn[{}]".format(mult, next(index)),
            driven_matrix * driver_matrix.inverse(),
            type="matrix",
        )

    # Setup the constraint connections
    cmds.connectAttr(driver_plug, "{}.matrixIn[{}]".format(mult, next(index)))
    cmds.connectAttr(
        "{}.parentInverseMatrix[0]".format(driven),
        "{}.matrixIn[{}]".format(mult, next(index)),
    )

    # Apply the constraint to the driven node
    name = driven + "_decomposeMatrix"
    decompose = cmds.createNode("decomposeMatrix", name=name)
    cmds.connectAttr(mult + ".matrixSum", decompose + ".inputMatrix")
    for attribute in (x + y for x in srt for y in "xyz"):
        cmds.connectAttr(
            "{}.o{}".format(decompose, attribute),
            "{}.{}".format(driven, attribute),
        )

    return mult
