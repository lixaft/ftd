"""Provide utilities related to attributes."""
import contextlib
import logging

from maya import cmds

import ftd.name

__all__ = ["disconnect", "divider", "move", "reset", "unlock"]

LOG = logging.getLogger(__name__)

SRT = tuple(x + y for x in "srt" for y in "xyz")
"""tuple: The translate, rotation, scale attributes for each axis."""


def disconnect(plug):
    """Disconnect the input connection of the given plug.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> a = cmds.createNode("transform", name="A")
        >>> b = cmds.createNode("transform", name="B")
        >>> _ = cmds.connectAttr(a + ".translateX", b + ".translateX")
        >>> disconnect(b + ".translateX")
        'A.translateX'

    Arguments:
        plug (str): The plug that should be disconnected.

    Returns:
        str: The source of the disconnected plug.
    """
    sources = cmds.listConnections(
        plug,
        source=True,
        destination=False,
        plugs=True,
    )
    source = (sources or [None])[0]
    if source:
        cmds.disconnectAttr(source, plug)
    return source


def divider(node, label=None):
    """Create an attribute separator for in the channel box.

    Warning:
        The actual name of the attribute created has nothing to do with the
        label parameter. It will be auto-generated using the
        :func:`~ftd.name.generate_unique` function. The real name should look
        like ``divider##`` with a unique index instead of the hash characters.

        Trying to access the attribute via this label will result in an error.

        See examples for details.

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
    """
    plug = ftd.name.generate_unique(node + ".divider##")
    cmds.addAttr(
        node,
        longName=plug.split(".")[-1],
        niceName=" ",
        attributeType="enum",
        # An string the contains only an escape character must be passed in a
        # blank label is requested, instead maya just put a 0 instead.
        enumName=label or " ",
    )
    cmds.setAttr(plug, channelBox=True)


def move(node, attribute, offset):
    """Move the position of the attribute in the channel box.

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

    with unlock(node):
        attributes = cmds.listAttr(userDefined=True)

        # This function can only move the attributes created by the user,
        # so make sure the specified attributes is one of them.
        if attribute not in attributes:
            msg = "Invalid plug '%s.%s'. Must be an user attribute."
            LOG.error(msg, node, attribute)
            return

        for _ in range(abs(offset)):
            index = attributes.index(attribute)

            to_last(attributes[index - (offset < 0)])
            for each in attributes[index + 1 + (offset > 0) :]:
                to_last(each)

            # Re-query all attributes again so that the index can be
            # recalculated correctly in the next iteration.
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
        if not cmds.getAttr(plug, settable=True):
            continue
        try:
            value = cmds.attributeQuery(attr, node=node, listDefault=True)[0]
            cmds.setAttr(plug, value)
        except RuntimeError:
            LOG.warning("Failed to reset '%s' plug.", plug)


@contextlib.contextmanager
def unlock(*args):
    """Temporarily unlock all attributes during the execution of the block.

    This function can be used to easily edit the locked attributes of a node.
    The attributes are first unlocked before the code is executed, and when the
    execution is finished,  the attributes are relocked.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> node = cmds.createNode("transform")
        >>> plug = node + ".translateX"
        >>> cmds.setAttr(plug, lock=True)
        >>> cmds.setAttr(plug, 1)  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
          ...
        RuntimeError
        >>> with unlock(node):
        ...     cmds.setAttr(plug, 1)
        >>> cmds.getAttr(plug, lock=True)
        True

    Arguments:
        *args: The nodes to unlock.
    """
    plugs = []
    for node in args:
        attributes = cmds.listAttr(node, locked=True) or []
        plugs.extend(["{}.{}".format(node, x) for x in attributes])

    for plug in plugs:
        cmds.setAttr(plug, lock=False)
    try:
        yield attributes
    finally:
        for plug in plugs:
            cmds.setAttr(plug, lock=True)
