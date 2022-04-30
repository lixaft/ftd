"""Provide utilities related to attributes."""
import contextlib
import io
import logging
import sys

from maya import cmds

__all__ = ["SRT", "copy", "separator", "move", "reset", "unlock"]

LOG = logging.getLogger(__name__)

TRANSLATE = ("translateX", "translateY", "translateZ")
ROTATE = ("rotateX", "rotateY", "rotateZ")
SCALE = ("scaleX", "scaleY", "scaleZ")
SHEAR = ("shearX", "shearY", "shearZ")

SRT = tuple(x + y for x in "srt" for y in "xyz")
"""tuple: All transformation attributes (short name)."""

LONG_SRT = TRANSLATE + ROTATE + SCALE
"""tuple: All transformation attributes (long name)."""


def copy(source, destination, attributes=None):
    # TODO: Currently this function only support long, short and bool
    # attributes. Need an implementation for:
    # - matrix
    # - compound
    # - enum
    # - double3
    # - string
    # TODO: Need to handle what should happen if attribute already exists on
    # the target node.
    # TODO: Update the docstring.
    """Copy the attribute(s) from the source node to the destination node.

    If no value is specified for the ``attributes`` parameter, all the user
    attributes of the source node will be copied.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> src = cmds.createNode("transform", name="src")
        >>> dst = cmds.createNode("transform", name="dst")
        >>> cmds.addAttr(src, longName="test")
        >>> cmds.objExists("dst.test")
        False
        >>> copy(src, dst)
        >>> cmds.objExists("dst.test")
        True

    Arguments:
        source (str): The name of the node from which the attribute(s) will be
            copied.
        destination (str): The name of the node to which the attribute(s) will
            be copied.
        attributes (list, optional): The list of attributes to copy.
    """
    attributes = attributes or cmds.listAttr(source, userDefined=True) or []

    for attribute in attributes:
        src_plug = "{}.{}".format(source, attribute)
        dst_plug = "{}.{}".format(destination, attribute)

        # Get all the information needed to create the copy.
        type_ = cmds.addAttr(src_plug, query=True, attributeType=True)
        locked = cmds.getAttr(src_plug, lock=True)
        visible = cmds.getAttr(src_plug, channelBox=True)
        keyable = cmds.getAttr(src_plug, keyable=True)
        value = cmds.getAttr(src_plug)
        default = cmds.addAttr(src_plug, query=True, defaultValue=True)

        # Create the attribute on the destination node.
        kwargs = {}
        kwargs["longName"] = attribute
        kwargs["attributeType"] = type_
        if default is not None:
            kwargs["defaultValue"] = default
        cmds.addAttr(destination, **kwargs)

        # Set attribute properties.
        cmds.setAttr(dst_plug, value)
        cmds.setAttr(dst_plug, channelBox=visible)
        cmds.setAttr(dst_plug, keyable=keyable)
        cmds.setAttr(dst_plug, lock=locked)


def separator(node, label=None):
    """Create a visual separator for the channel box using a dummy attribute.

    This create a maya enum attribute at the last position of the channel box.

    The name section will be left empty, and the enum section will be filled
    with the value specified in the ``label`` parameter. If no value is
    specified, a series of dashes (``-``) will be used instead.

    The attribute name itself will be automatically generated with an index at
    the end which will be incremented by 1 until a unique name is found.
    This should result in something like:
    ``separator 00``, ``separator 01``, ``separator02``, ...

    Note:
        If there are more that 99 separators on the same node (I don't really
        see any reasons for that but why not xD), the index of the attribute
        name will continue to grow using a padding of three:
        ``separator 100``, ``separator 101``, ``separator102``...

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> node = cmds.createNode("transform", name="A")
        >>> separator(node, label="Others")
        'A.separator00'
        >>> separator(node, label="Others")
        'A.separator01'
        >>> cmds.objExists(node + ".Others")
        False
        >>> cmds.objExists(node + ".separator00")
        True

    Arguments:
        node (str): The name of the node on which create the separator.
        label (str, optional): The text that will be used on the separator.

    Returns:
        str: The name of the created plug.
    """
    # Generate an unique attribute name.
    index = 0
    base = "{}.separator{:02}"

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
        # TODO: The `Undo:` displayed in the output windows should be removed
        # but this seems to be done at the C level (with MGlobal.displayInfo)
        # and therefore cannot be simply redirected with sys.stdout. If anyone
        # have any ideas, please let me know! :)
        old = sys.stdout
        sys.stdout = io.BytesIO()
        try:
            cmds.undo()
        finally:
            sys.stdout = old

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


@contextlib.contextmanager
def restore(nodes):
    """Restore the nodes before the action."""
    for node in nodes:
        cmds.nodePreset(save=(node, node))
    yield
    for node in nodes:
        cmds.nodePreset(load=(node, node))
        cmds.nodePreset(delete=(node, node))
