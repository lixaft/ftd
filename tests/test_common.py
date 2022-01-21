# pylint: disable=unused-argument
"""Test the common module."""
import pytest

from maya import cmds

import ftd.common


def test_exec_string(newscene):
    """Test executin string in python or mel."""

    ftd.common.exec_string('createNode "transform" -name "A"', language="mel")
    ftd.common.exec_string(
        'import maya\nmaya.cmds.createNode("transform", name="B")',
        language="python",
    )
    assert cmds.objExists("A")
    assert cmds.objExists("B")

    with pytest.raises(ValueError):
        ftd.common.exec_string("polyCube", language="unknown")

    def decorator(func):
        cmds.createNode("transform", name="C")
        return func

    ftd.common.exec_string("None", decorators=[decorator])
    assert cmds.objExists("C")
