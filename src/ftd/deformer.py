"""This module provides utilities for common tasks involving deformers."""
import logging

from maya import cmds

import ftd.graph
import ftd.name

__all__ = ["blendshape"]

LOG = logging.getLogger(__name__)


def blendshape(driver, driven, name="blendshape", alias=None, weight=1):
    """Create a new blendshape between the two specified shapes.

    First look in the history of the shape if there is not already a
    blendshape available. If so, add the driver directly to the next
    available target.

    Arguments:
        str (driver): The name of the driver node.
        str (driven): The name of the driven node.
        name (str): The name of the new blendshape.
        alias (str): The alias name of the driver shape.
        weight (float): The default weight of the target.

    Returns:
        str: The name of the blendshape node where the driver was added.
    """
    bs_node = ftd.graph.find_related(driven, type="blendShape")
    index = 0

    if bs_node:
        # If a blendshape already exists, find the first index where the
        # target can be attached and connect it to this attribute.
        plug = (
            "{}.inputTarget[0].inputTargetGroup[{}]"
            ".inputTargetItem[6000].inputGeomTarget"
        )
        while cmds.listConnections(plug.format(bs_node, index), source=True):
            index += 1

        cmds.blendShape(
            bs_node,
            edit=True,
            target=(driven, index, driver, 1.0),
            weight=(index, weight),
        )
    else:
        # If no blendshape yet deforms the node, quick and easy:
        # create the blendshape!
        bs_node = cmds.blendShape(
            driver,
            driven,
            name=ftd.name.generate_unique(name),
            weight=(0, weight),
        )

    if alias:
        cmds.aliasAttr(alias, "{}.weight{}]".format(bs_node, index))
    return bs_node
