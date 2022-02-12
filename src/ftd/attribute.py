# coding: utf-8
"""Provide utilities related to attributes."""
import contextlib
import logging

from maya import cmds, mel

__all__ = [
    "SRT",
    "disconnect",
    "divider",
    "move",
    "next_available",
    "reset",
    "unlock",
]

LOG = logging.getLogger(__name__)

SRT = tuple(x + y for x in "srt" for y in "xyz")
"""tuple: All transformation attributes (short name)."""


def disconnect(plug):
    """Break the input connection of the given plug.

    Schema:
        ┌──────────┐      ┌──────────┐
        │          ■──//──■          │
        └──────────┘      └──────────┘

    Disconnect the plug from its source and return the name of the source plug.

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
        str: The source name of the disconnected plug.

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
    """Create visual separator for attribute in the channel box.

    Schema:
        │ Attr1  0.0        │
        │       █────────── │
        │ Attr2  0.0        │

    If a label parameter is specified, the dashes will be replaced by the value
    given to the parameter.

    The name of the attribute will be generated automatically by the function
    in order to get something without the user having to worry about it.

    The attribute will be named ``divider00``, ``divider01`` and so on.

    Note:
        If there are more than 99 dividers on a node (although I don't see when
        this will happen xD) the function will continue with a padding of 3:
        100, 101 and so on.

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
        label (str, optional): The displayed name of the separator.

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

    Schema:
        ┌> │ Attr1 █ 0.0 │ ─┐
        │  │ Attr2 █ 0.0 │ <┤
        └─ │ Attr3 █ 0.0 │ <┘

    Offset the position of the attribute in the channel box the number of times
    specified by the offset parameter. The parameter accepts both positive
    (upward) and negative (downward) values.

    Default attributes (those created by maya) cannot be moved using this
    function. See the examples for details.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> node = cmds.createNode("transform", name="A")
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
        # any ideas, please let me know! :)
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


def next_available(plug, start=0):
    """Find the next available index of a multi attribute.

    Schema:
        ■ multi
        ├─■ multi[0]
        ├─■ multi[1]
        ├─■ ...

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> src = cmds.createNode("multMatrix", name="src")
        >>> dst = cmds.createNode("multMatrix", name="dst")
        >>> next_available(dst + ".matrixIn")
        'dst.matrixIn[0]'
        >>> _ = cmds.connectAttr(src + ".matrixSum", dst + ".matrixIn[0]")
        >>> next_available(dst + ".matrixIn")
        'dst.matrixIn[1]'

    Arguments:
        plug (str): The name of the multi attribute plug.
        start (int): The index from which the search should be start.

    Returns:
        str: The next available plug of the multi attribute.
    """
    index = mel.eval("getNextFreeMultiIndex {} {}".format(plug, start))
    return "{}[{}]".format(plug, index)


def reset(node, attributes=None):
    """Reset the attributes to their default values.

    If no attributes is specified reset all the keyable attributes of the node.

    Tip:
        To edito the default value of an existing attribute, you can use the
        ``defaultValue`` parameter of the :func:`cmds.addAttr` command.
        More information on the `official documentation`_.

    Todo:
        On linux it seems that sometimes the .scale failed to reset.

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
        attributes (list, optional): The attributes to reset.

    .. _official documentation:
        https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/CommandsPython/addAttr.html#flagdefaultValue
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

    Schema:
         ┌─────┐
         │     │
        ┌──────┴┐
        │   █   │
        │   │   │
        └───────┘

    This function can be used to easily edit the locked attributes of a node.
    The attributes are first unlocked before the code is executed, and when the
    execution is finished, the attributes are relocked.

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
