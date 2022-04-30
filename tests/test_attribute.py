"""Test for attribute."""
import pytest

from maya import cmds

import ftd.attribute


@pytest.mark.parametrize(
    "attributes",
    [
        [{"longName": "long", "attributeType": "long"}],
        [{"longName": "short", "attributeType": "short"}],
        [{"longName": "bool", "attributeType": "bool"}],
    ],
    ids=["long", "short", "bool"],
)
def test_copy_attributes(attributes):
    """Test to copy simple attribute types."""
    src = cmds.createNode("transform")
    dst = cmds.createNode("transform")

    # Create the attributes.
    for flags in attributes:
        cmds.addAttr(src, **flags)

    # Perform the copy.
    ftd.attribute.copy(src, dst)

    # Compare the attributes.
    for flags in attributes:
        src_plug = "{}.{}".format(src, flags["longName"])
        dst_plug = "{}.{}".format(dst, flags["longName"])
        assert cmds.objExists(dst_plug)
        assert cmds.getAttr(src_plug) == cmds.getAttr(dst_plug)


@pytest.mark.parametrize("amount", [1, 10, 102])
@pytest.mark.parametrize("label", [None, "", "text"])
def test_create_separator(amount, label):
    # TODO: Check the copied attributes.
    """Test to create attributre separator on a single node."""
    node = cmds.createNode("transform")
    for _ in range(amount):
        ftd.attribute.separator(node, label)


def test_move_attribute():
    """Test to move an attribute aloung the channel box."""
    node = cmds.createNode("transform")
    cmds.addAttr(node, longName="_a")
    cmds.addAttr(node, longName="_b")
    cmds.addAttr(node, longName="_c")
    cmds.addAttr(node, longName="_d")
    cmds.addAttr(node, longName="_e")

    ftd.attribute.move(node, attribute="_a", offset=3)
    assert cmds.listAttr(userDefined=True) == ["_b", "_c", "_d", "_a", "_e"]
