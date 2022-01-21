"""Provide utilities related to attributes."""
import contextlib
import logging

from maya import cmds

__all__ = ["disconnect", "divider", "move", "reset", "unlock"]

LOG = logging.getLogger(__name__)

SRT = tuple(x + y for x in "srt" for y in "xyz")
"""tuple: The translate, rotation, scale attributes for each axis."""


def disconnect(plug):
    """Break the connection of the given plug.

    ┌─────────┐      ┌─────────┐
    │         ├──//──┤         │
    └─────────┘      └─────────┘

    Disconnect the plug from its source and return the source plug name.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> a = cmds.createNode("transform", name="A")
        >>> b = cmds.createNode("transform", name="B")
        >>> _ = cmds.connectAttr(a + ".translateX", b + ".translateX")
        >>> disconnect(b + ".translateX")
        'A.translateX'

    Arguments:
        plug (str): The name of the plug to disconnect.

    Returns:
        str: The source of the disconnected plug.
            If the plug passed as argument doesn't have any source connection,
            return None.
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
    """Create an attribute separator in channel box.

    │                   │
    │ Attr1  0.0        │
    │       █────────── │
    │ Attr2  0.0        │
    │                   │

    If a label is specified, the line separator will be replaced by the string
    passed to the parameter.

    The name of the attribute will be generated automatically by the function
    to get something unique that will not block any possibility for real
    attributes for which names are important.

    The attributes will be named `divider00`, `divider01` and so on.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> node = cmds.createNode("transform", name="A")
        >>> divider(node, label="Others")
        'A.divider00'
        >>> divider(node, label="Others")
        'A.divider01'
        >>> cmds.objExists(node + ".Others")
        False
        >>> cmds.objExists(node + ".divider00")
        True

    Arguments:
        node (str): The name of the node on which the divider will be created.
        label (str): The displayed name of the separator.

    Returns:
        str: The name of the plug separator.
    """
    # Generate an unique attribute name.
    index = 0
    base = "{}.divider{:02}"

    plug = base.format(node, index)
    while cmds.objExists(plug):
        index += 1
        plug = base.format(node, index)

    # Create the attribute and make it visible.
    cmds.addAttr(
        node,
        longName=plug.split(".", 1)[-1],
        niceName=" ",
        attributeType="enum",
        enumName=label or ("-" * 15),
    )
    cmds.setAttr(plug, channelBox=True)
    return plug


def move(node, attribute, offset):
    """Move the position of the attribute in the channel box.

       │             │
    ┌> │ Attr1 █ 0.0 │ ─┐
    │  │ Attr2 █ 0.0 │  │
    └─ │ Attr3 █ 0.0 │ <┘
       │             │

    Moves the attribute up or down by the number of indexes specified by the
    offset parameter. Use a positive value to move the attribute upwards and
    negative to move it downwards.

    See default attributes (The one that is be created by maya) can be moved
    using the function. See examples for detailes.

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
        Traceback (most recent call last):
          ...
        AttributeError

    Arguments:
        node (str): The node under which the attribute exists.
        attribute (str): The name of the attribute to move.
        offset (int): How much should the attribute be moved?
            This value can be positive or negative.

    Raises:
        AttributeError: The attribute is not an user attribute.
    """

    def to_last(attr):
        cmds.deleteAttr(node, attribute=attr)
        # The `Undo:` displayed in the output windows should be removed but
        # this seems to be done at the C level (with MGlobal.displayInfo) and
        # therefore cannot be simply redirected with sys.stdout. If anyone have
        # any ideas, please let me know.
        cmds.undo()

    with unlock(node):
        attributes = cmds.listAttr(userDefined=True)

        # This function can only move the attributes created by the user,
        # so make sure the specified attributes is one of them.
        if attribute not in attributes:
            msg = "Invalid plug '{}.{}'. Must be an user attribute."
            raise AttributeError(msg.format(node, attribute))

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
        :func:`cmds.setAttr` command and the ``defaultValue`` flag.

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
        except BaseException:
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
