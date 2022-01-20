"""Provide utilities related to deformers."""
import logging

from maya import cmds

import ftd.graph
import ftd.name

__all__ = ["blendshape", "clean_orig", "cluster"]

LOG = logging.getLogger(__name__)


def find(node, sets=False, type=None):
    """Find all the deformers associated to the node.

    Arguments:
        node (str): The name of node on which find the deformers.
        sets (bool): Return the deformer sets instead of the deformers.
        type (str): Filter the type of the returned deformers.

    Retruns:
        list: An array that will contains all the deofmers of the shape.
    """
    result = []
    for deformer in cmds.findDeformers(node):
        if type is not None and cmds.nodeType(deformer) != type:
            continue
        if sets:
            set_ = ftd.graph.find_related(
                deformer, direction="dn", type="objectSet"
            )
            result.append(set_)
        else:
            result.append(deformer)
    return result


def blendshape(driver, driven, name="blendshape", alias=None, weight=1.0):
    """Create a new blendshape between the two specified shapes.

    First look in the history of the shape if there is not already a
    blendshape available. If so, add the driver directly to the next
    available target.

    Arguments:
        driver (str): The name of the driver node.
        driven (str): The name of the driven node.
        name (str): The name of the new blendshape.
        alias (str): The alias name of the driver shape.
        weight (float): The default weight of the target.

    Returns:
        str: The name of the blendshape node where the driver was added.
    """
    bs_node = ftd.graph.find_related(driven, type="blendShape")
    index = 0

    # If a blendshape already exists, find the first index where the
    # target can be attached and connect it to this attribute.
    if bs_node:
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
    # If no blendshape is already attached to the geometry, quick and easy:
    # create the blendshape! :)
    else:
        bs_node = cmds.blendShape(
            driver,
            driven,
            name=ftd.name.generate_unique(name),
            weight=(0, weight),
        )

    if alias:
        cmds.aliasAttr(alias, "{}.weight{}]".format(bs_node, index))
    return bs_node


def clean_orig(node=None):
    """Clean the unused original shapes.

    Remove the unused ShapeOrig to increase the FPS of the scene.
    If no arguments is specified, operate on all nodes in the scene.

    Arguments:
        node (str, optional): The node that need to be cleaned.
    """
    if node:
        shapes = cmds.ls(node, intermediateObjects=True, dagObjects=True)
    else:
        shapes = cmds.ls(intermediateObjects=True, dagObjects=True)
    for shape in shapes:
        if not cmds.listConnections(shape, type="groupParts"):
            cmds.delete(shape)


def cluster(obj, name=None):
    """Create a new cluster with world transformation."""
    if not name:
        name = ftd.name.generate_unique("cluster#")

    old = cmds.cluster(obj)[1]
    new = cmds.createNode("transform", name=name)
    shape = cmds.listRelatives(old, shapes=True)[0]

    cmds.matchTransform(new, old)
    cmds.setAttr(shape + ".origin", 0, 0, 0)
    cmds.cluster(
        shape,
        edit=True,
        weightedNode=[new, new],
        bindState=True,
    )
    cmds.delete(old)
    new = cmds.rename(new, name)
    cmds.rename(shape, new + "Shape")
    return new
