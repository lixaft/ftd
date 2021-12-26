"""Provide utilities related to constraints."""
import logging

from maya import cmds
from maya.api import OpenMaya

import ftd.attribute
import ftd.graph

__all__ = ["matrix"]

LOG = logging.getLogger(__name__)


def matrix(
    driver,
    driven,
    offset=False,
    hierarchy=False,
    decompose=False,
    srt="srt",
):
    """Constrains two nodes using matrices.

    Examples:
        >>> from maya import cmds
        >>> a = cmds.polyCube(name="a")[0]
        >>> b = cmds.polyCube(name="b")[0]
        >>> cmds.setAttr(b + ".translateX", 10)
        >>> matrix(a, b, offset=True)
        ['a_multMatrix']

    Arguments:
        driver (str): The parent node.
        driven (str): The child node.
        offset (bool): Maintain the distance between the two nodes.
        hierarchy (bool): Add the inverted parent matrix.
        decompose (bool): Add a decomposition matrix to connect the transform.
        srt (str): Attributes to connect.

    Returns:
        list: The nodes created by the constraint.
    """
    if "." in driver:
        pdriver = driver
        driver = driver.split(".", 1)[0]
    else:
        pdriver = driver + ".worldMatrix[0]"
    pdriven = driven + ".worldMatrix[0]"

    # Track all the nodes create by the setup to rename them at once
    nodes = []

    # Calculte the matrix
    if offset or hierarchy:
        mult = cmds.createNode("multMatrix")
        nodes.append(mult)

        if offset:
            mdriver = OpenMaya.MMatrix(cmds.getAttr(pdriver))
            mdriven = OpenMaya.MMatrix(cmds.getAttr(pdriven))
            local = mdriven * mdriver.inverse()
            cmds.setAttr(mult + ".matrixIn[0]", local, type="matrix")

        cmds.connectAttr(pdriver, mult + ".matrixIn[1]")

        if hierarchy:
            cmds.connectAttr(
                driven + ".parentInverseMatrix",
                mult + ".matrixIn[2]",
            )

        pdriver = "{}.matrixSum".format(mult)

    # Connect the matrix to translate, rotate, scale plug
    if decompose:
        decompose = cmds.createNode("decomposeMatrix")
        nodes.append(decompose)
        cmds.connectAttr(pdriver, decompose + ".inputMatrix")
        for attribute in (x + y for x in srt for y in "xyz"):
            cmds.connectAttr(
                "{}.o{}".format(decompose, attribute),
                "{}.{}".format(driven, attribute),
            )
    else:
        if srt != "srt":
            pick = cmds.createNode("pickMatrix", name=driver + "_pickMatrix")
            nodes.append(pick)
            cmds.connectAttr(pdriver, pick + ".inputMatrix")
            pdriver = pick + ".outputMatrix"
            for key, attribute in {"t": "tra", "r": "rot", "s": "sca"}.items():
                cmds.setAttr("{}.{}".format(pick, attribute), key in srt)

        cmds.connectAttr(pdriver, driven + ".offsetParentMatrix")
        ftd.attribute.reset(driven, [x + y for x in srt for y in "xyz"])

    # Rename the created nodes
    for index, node in enumerate(nodes):
        new = cmds.rename(node, "{}_{}".format(driver, cmds.nodeType(node)))
        nodes[index] = new

    return nodes
