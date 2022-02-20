"""Provide utilities related to colors."""
import logging
import os

import yaml

from maya import cmds

__all__ = ["COLORS", "index", "name", "rgb"]

LOG = logging.getLogger(__name__)

COLORS = {}
"""dict: The available colors.

:meta hide-value:
"""

# Populate the colors data.
_PATH = os.path.join(os.path.dirname(__file__), "configs", "colors.yaml")
with open(_PATH, "r") as _stream:
    COLORS.update(yaml.load(_stream, Loader=yaml.FullLoader))
del _PATH, _stream


def index(node, value=0):
    """Set the color of a node using the maya index.

    Tip:
        It's possible to query and edit the maya default index color by using
        the :func:`colorIndex` command.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> node = cmds.circle()[0]
        >>> index(node, 18)
        >>> cmds.getAttr(node + ".overrideColor")
        18
        >>> index(node)
        >>> cmds.getAttr(node + ".overrideColor")
        0

    Arguments:
        node (str): The target node.
        value (int): The index color between 0 and 31.
            The value 0 corresponds to the default color of the node.

    Raises:
        ValueError: The provided value is not in the valid range.
    """
    if not 0 <= value <= 31:
        raise ValueError("The index color must be between 0 and 31.")
    cmds.setAttr(node + ".overrideEnabled", True)
    cmds.setAttr(node + ".overrideRGBColors", False)
    cmds.setAttr(node + ".overrideColor", value)


def name(node, value):
    """Set the RGB color using CSS color names.

    The website `w3schools`_ references all the available
    colors classed by names, values or groups.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> node = cmds.circle()[0]
        >>> name(node, "red")
        >>> cmds.getAttr(node + ".overrideColorRGB")[0]
        (1.0, 0.0, 0.0)

    Arguments:
        node (str): The target node.
        value (str): The color name.

    .. _w3schools:
        https://www.w3schools.com/colors/colors_groups.asp
    """
    rgb(node, COLORS[value]["rgb"])


def rgb(node, values, max_range=255):
    """Set the color of a node using RGB values.

    Caution:
        This function work is a rgb range between 0 and 255. However, maya
        uses an internal range between 0 and 1. It's still possible to work
        with the maya range by setting the ``max_range`` parameter to 1.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> node = cmds.circle()[0]
        >>> rgb(node, (255, 0, 0))
        >>> cmds.getAttr(node + ".overrideColorRGB")[0]
        (1.0, 0.0, 0.0)
        >>> rgb(node, (1, 0, 1), max_range=1)
        >>> cmds.getAttr(node + ".overrideColorRGB")[0]
        (1.0, 0.0, 1.0)

    Arguments:
        node (str): The target node.
        values (tuple): The RGB values as tuple.
        max_range (int): The maximum color value. Usually 1 or 255.
    """
    cmds.setAttr(node + ".overrideEnabled", True)
    cmds.setAttr(node + ".overrideRGBColors", True)
    cmds.setAttr(node + ".overrideColorRGB", *(x / max_range for x in values))
