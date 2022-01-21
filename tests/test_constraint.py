# pylint: disable=unused-argument
"""test the constraint module."""
import pytest

from maya import cmds

import ftd.constraint


def test_matrix(newscene):
    """Test the constraint matrix function."""
    driver = cmds.createNode("transform", name="A")

    driven = cmds.createNode("transform", name="B")
    ftd.constraint.matrix(driver, driven)
    cmds.setAttr(driver + ".translateY", 2)
    assert cmds.getAttr(driven + ".translateY") == 2

    driven = cmds.createNode("transform", name="C")
    ftd.constraint.matrix(driver, driven, offset=True)
    cmds.setAttr(driver + ".translateX", 2)
    assert cmds.getAttr(driven + ".translate")[0] == (2.0, 0.0, 0.0)

    driven = cmds.createNode("transform", name="D")
    ftd.constraint.matrix(driver + ".worldInverseMatrix[0]", driven)
    assert cmds.getAttr(driven + ".translate")[0] == (-2.0, -2.0, 0.0)

    driven = cmds.createNode("transform", name="E")
    with pytest.raises(ValueError):
        ftd.constraint.matrix(driver + ".translateX", driven)

    node = cmds.createNode("addDoubleLinear", name="DG")
    with pytest.raises(ValueError):
        ftd.constraint.matrix(node, driven)
    with pytest.raises(ValueError):
        ftd.constraint.matrix(driven, node)
