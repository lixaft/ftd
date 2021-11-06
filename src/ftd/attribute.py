"""This module provides utilities for common tasks involving attributes."""
import logging

from maya import cmds

import ftd.name

__all__ = ["divider", "move", "reset"]

LOG = logging.getLogger(__name__)

SRT = tuple(x + y for x in "srt" for y in "xyz")
"""tuple: The translate, rotation, scale attributes for each axis."""


def divider(node, label=None, look="basic"):
    # pylint: disable=unused-argument
    """Create a fake attribute that will visually make a separator.

    It's possible to choose between different divider style:

    .. csv-table::
        :header: Value, Look

        ``basic``,

    Warning:
        The actual name of the attribute created has nothing to do with the
        label parameter. It will be auto-generated using the
        :func:`~ftd.name.generate_unique` function. The real name should look
        like ``divider##`` with a unique index instead of the hash characters.

        Trying to access the attribute via this label will result in an error.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> node = cmds.createNode("transform")
        >>> divider(node, label="Others")
        >>> cmds.objExists(node + ".Others")
        False
        >>> cmds.objExists(node + ".divider00")
        True

    Arguments:
        node (str): The name of the node on which the divider will be created.
        label (str): The displayed name of the separator.
        look (str): The look of the separator.

    Todo:
        Implement different divider look.
    """
    plug = ftd.name.generate_unique(node + ".divider##")
    cmds.addAttr(
        node,
        longName=plug.split(".")[-1],
        niceName=" ",
        attributeType="enum",
        # thanks to maya, it writes a 0 if the value None is passed...
        enumName=label or " ",
    )
    cmds.setAttr(plug, channelBox=True)


def move(node, attribute, offset):
    """Move the position of the attribute in the channelBox.

    .. admonition:: Limitations...
        :class: error

        You can only move attributes created by the user.
        e.g the ``translateX`` attribute can be move.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> node = cmds.createNode("transform")
        >>> cmds.addAttr(node, longName="a", keyable=True)
        >>> cmds.addAttr(node, longName="b", keyable=True)
        >>> cmds.addAttr(node, longName="d", keyable=True)
        >>> move(node, "d", offset=2)
        >>> move(node, "a", offset=-1)
        >>> move(node, "translateX", offset=1)

    Arguments:
        node (str): The node under which the attribute exists.
        attribute (str): The name of the attribute to move.
        offset (int): How much should the attribute be moved?
            This value can be positive or negative.
    """

    def to_last(attr):
        cmds.deleteAttr(node, attribute=attr)
        # The `Undo:` displayed in the output windows should be removed
        # but this seems to be done at the C level (with MGlobal.displayInfo)
        # and therefore cannot be simply redirected with sys.stdout.
        cmds.undo()

    with ftd.context.unlock(node):
        attributes = cmds.listAttr(userDefined=True)

        # this function can only move the attributes created by the user,
        # so make sure the specified attributes is one of them
        if attribute not in attributes:
            msg = "Invalid plug '%s.%s'. Must be an user attribute."
            LOG.error(msg, node, attribute)
            return

        for _ in range(abs(offset)):
            index = attributes.index(attribute)

            to_last(attributes[index - (offset < 0)])
            for each in attributes[index + 1 + (offset > 0) :]:
                to_last(each)

            attributes = cmds.listAttr(userDefined=True)


def reset(node, attributes=None):
    """Reset the attributes to thei default values.

    Tip:
        The default value of an attribute can be edited with the
        :func:`cmds.setAttr` command and the ``defaultValue`` parameter.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> node = cmds.createNode("transform")
        >>> cmds.setAttr(node + ".translateX", 10)
        >>> cmds.setAttr(node + ".scaleX", 3)
        >>> reset(node)
        >>> cmds.getAttr(node + ".translateX")
        0.0
        >>> cmds.getAttr(node + ".scaleX")
        1.0

    Arguments:
        node (str): The node containing the attributes to reset.
        attributes (list): The attributes to reset.
            By default, reset all keyable attributes.
    """
    for attr in attributes or cmds.listAttr(node, keyable=True):
        plug = "{}.{}".format(node, attr)
        if cmds.getAttr(plug, settable=True):
            value = cmds.attributeQuery(attr, node=node, listDefault=True)[0]
            cmds.setAttr(plug, value)
