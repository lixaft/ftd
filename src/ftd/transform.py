"""Provide utilities related to transform."""
import functools
import logging
import math

from maya import cmds

__all__ = ["create_and_match"]

LOG = logging.getLogger(__name__)


def create_and_match(func):
    """Improves the way to create nodes."""

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        selection = cmds.ls(selection=True) or [""]

        if "." in selection[0]:
            tool = "Move"
            cmds.setToolTo(tool)
            pos = cmds.manipMoveContext(tool, query=True, position=True)
            ori = cmds.manipMoveContext(tool, query=True, orientAxes=True)

            func_return = func(*args, **kwargs)
            cmds.setAttr(func_return + ".translate", *pos)
            cmds.setAttr(func_return + ".rotate", *map(math.degrees, ori))
            return [func_return]

        list_return = []
        for _, node in enumerate(selection):
            func_return = func(*args, **kwargs)
            if node:
                cmds.matchTransform(func_return, node)
            list_return.append(func_return)

        cmds.select(list_return)
        return list_return

    return _wrapper
