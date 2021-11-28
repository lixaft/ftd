"""Provide utilities related to joints."""
import logging

from maya import cmds

__all__ = ["show_orient"]

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
