# pylint: disable=unused-argument
"""Test the :mod:`ftd.attribute` module."""
from maya import cmds

import ftd.attribute


def test_disconnect(newscene):
    """The the disconnect function."""
    node_a = cmds.createNode("transform", name="A")
    node_b = cmds.createNode("transform", name="B")
    cmds.connectAttr(node_a + ".translateX", node_b + ".translateY")

    assert ftd.attribute.disconnect(node_b + ".translateX") is None
    assert ftd.attribute.disconnect(node_b + ".translateY") == "A.translateX"


def test_divider(newscene):
    """Test the creation of divider attribute."""
    node = cmds.createNode("transform", name="A")

    ftd.attribute.divider(node)
    ftd.attribute.divider(node, "A")
    ftd.attribute.divider(node, "A")
    assert cmds.attributeQuery("divider00", node=node, exists=True)
    assert cmds.attributeQuery("divider01", node=node, exists=True)
    assert cmds.attributeQuery("divider02", node=node, exists=True)


def test_reset(newscene):
    """Test to the reset function."""
    node = cmds.createNode("transform", name="A")

    cmds.setAttr(node + ".translate", 1, 1, 1)
    cmds.setAttr(node + ".translateX", lock=True)
    cmds.setAttr(node + ".translateY", keyable=False, channelBox=True)

    ftd.attribute.reset(node)
    assert cmds.getAttr(node + ".translate")[0] == (1.0, 1.0, 0.0)

    ftd.attribute.reset(node, ["translateX", "translateY", "translateZ"])
    assert cmds.getAttr(node + ".translate")[0] == (1.0, 0.0, 0.0)

    cmds.addAttr(node, longName="inputMatrix", attributeType="matrix")
    ftd.attribute.reset(node, ["inputMatrix"])
