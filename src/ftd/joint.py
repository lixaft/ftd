"""Provide utilities related to joints."""
from __future__ import division

import logging

from maya import cmds
from maya.api import OpenMaya

__all__ = ["show_orient", "parent", "set_radius"]

LOG = logging.getLogger(__name__)


def show_orient(state, joints=None):
    """Show or hide the display of the joint orientation axes.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> jnt = cmds.createNode("joint", name="A")
        >>> cmds.getAttr(jnt + ".displayLocalAxis")
        False
        >>> show_orient(True)
        >>> cmds.getAttr(jnt + ".displayLocalAxis")
        True

    Arguments:
        state (bool): Show or hide the axis visibility.
        joints (list, optinal): The list of joints on which edit the visible
            state of orientation axis. By default, edit all joints present in
            the scene.
    """
    for joint in joints or cmds.ls(type="joint"):
        cmds.setAttr(joint + ".displayLocalAxis", state)


def parent(child, target):
    """Parent joint."""
    mtx = cmds.xform(child, query=True, matrix=True, worldSpace=True)
    cmds.parent(child, target, relative=True)
    cmds.setAttr(child + ".jointOrient", 0, 0, 0)
    cmds.xform(child, matrix=mtx, worldSpace=True)


def set_radius(root, method="average", multiplier=1.0, recurse=False):
    """Define the radius of a joint based to its distance from its children.

    Schema:
            ┌───■
        ■───┼───■
            └───■────■

    Arguments:
        root (str): The root joint on which the radius should be set.
        method (str): The method to use in case of multiple children.
        multiplier (float): The radius multiplier.
        recurse (bool): Also affects all joints descending from the root.

    Raises:
        ValueError: The value passed to the parameter ``method`` is not valid.
    """

    def get_point(node):
        pos = cmds.xform(node, query=True, translation=True, worldSpace=True)
        return OpenMaya.MPoint(pos)

    root_pos = get_point(root)

    # Let's find and register the distance between the root and each of its
    # children.
    distances = []
    for child in cmds.listRelatives(root, children=True, type="joint") or []:
        distances.append(root_pos.distanceTo(get_point(child)))

        # Make the recursion.
        if recurse:
            set_radius(child, method, multiplier, recurse)

    # If not valid children are found just set the radius to 1
    if not distances:
        value = 10
    elif method == "average":
        value = sum(distances) / len(distances)
    elif method == "minimum":
        value = min(distances)
    elif method == "maximum":
        value = max(distances)
    else:
        raise ValueError("Invalid method value.")

    cmds.setAttr(root + ".radius", value * 0.1 * multiplier)
