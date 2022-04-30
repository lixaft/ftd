"""Provide utilities related to selection."""
import functools

from maya import cmds
from maya.api import OpenMaya, OpenMayaUI


def from_viewport():
    """Select all objects visible in the given viewport"""
    viewport = OpenMayaUI.M3dView.active3dView()
    OpenMaya.MGlobal.selectFromScreen(
        0,
        0,
        viewport.portWidth(),
        viewport.portHeight(),
        OpenMaya.MGlobal.kReplaceList,
        OpenMaya.MGlobal.kWireframeSelectMethod,
    )


def mirror(selection, sides=None):
    """Mirror the current selected object."""
    # Build the side data.
    sides = (sides or {"l": "r"}).copy()
    for key, value in sides.items():
        data = {}
        data[key.upper()] = value.upper()
        data[key.lower()] = value.lower()
        data[value.upper()] = key.upper()
        data[value.lower()] = key.lower()
        sides.update(data)

    for each in selection:
        tokens = each.split("_")
        for old, new in sides.items():
            try:
                index = tokens.index(old)
                tokens[index] = new
            except ValueError:
                continue

        node = "_".join(tokens)
        if node != each in cmds.objExists(node):
            yield node


def keep_selected(func):
    """Keep the selection unchanged after the execution of the function."""

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        sel = cmds.ls(selection=True)
        returned = func(*args, **kwargs)
        if sel:
            cmds.select(sel)
        else:
            cmds.select(clear=True)
        return returned

    return _wrapper
