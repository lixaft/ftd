"""Test the color module."""
import pytest

from maya import cmds

import ftd.color


def test_set_color_using_index():
    """Test the color index function."""
    node = cmds.createNode("transform", name="A")
    ftd.color.index(node, 0)
    ftd.color.index(node, 31)

    with pytest.raises(ValueError):
        ftd.color.index(node, -1)
    with pytest.raises(ValueError):
        ftd.color.index(node, 32)
