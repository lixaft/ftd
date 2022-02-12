"""Test the :mod:`ftd.attribute` module."""

import pytest

from maya import cmds

import ftd.attribute


def test_disconnect_attribute():
    """Test to dosconnect two attributes."""
    node_a = cmds.createNode("transform", name="A")
    node_b = cmds.createNode("transform", name="B")
    cmds.connectAttr(node_a + ".translateX", node_b + ".translateY")

    assert ftd.attribute.disconnect(node_b + ".translateX") is None
    assert ftd.attribute.disconnect(node_b + ".translateY") == "A.translateX"


@pytest.mark.parametrize("label", (None, "", " ", "Divider"))
def test_divider_attribute(label):
    """Test to create a divider attribute."""
    node = cmds.createNode("transform", name="A")

    assert ftd.attribute.divider(node, label) == "A.divider00"
    assert ftd.attribute.divider(node, label) == "A.divider01"
    assert ftd.attribute.divider(node, label) == "A.divider02"

    for attribute in ("divider00", "divider01", "divider02"):
        assert cmds.attributeQuery(attribute, node=node, exists=True)
        enum = cmds.attributeQuery("divider00", node=node, listEnum=True)
        assert enum != attribute
        assert enum == [label or "-" * 15]


def test_reset_attribute_values():
    """Test to reset attributes to their default value."""
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
