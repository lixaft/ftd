"""Provide context manager."""
import contextlib
import cProfile
import logging
import pstats

from maya import cmds

__all__ = ["profile", "undo", "unlock"]

LOG = logging.getLogger(__name__)


@contextlib.contextmanager
def profile(sort="time", lines=None, strip=False):
    """Detail the execution of all statements in the block.

    The following are the values accepted by the ``sort`` parameter:

    .. csv-table::
        :header: Value, Description

        ``calls``,        Call count
        ``cumulative``,   Cumulative time
        ``filename``,     File name
        ``pcalls``,       Primitive call count
        ``line``,         Line number
        ``name``,         Function name
        ``nfl``,          Name/file/line
        ``stdname``,      Standard name
        ``time``,         Internal time

    Arguments:
        sort (str): Sorts the output according to the specified mode.
        lines (int): Limits the output to a specified number of lines.
        strip (bool): Removes all leading path information from file name.
    """
    profile_ = cProfile.Profile()
    try:
        profile_.enable()
        yield
    finally:
        profile_.disable()

    stats = pstats.Stats(profile_)
    if strip:
        stats.strip_dirs()
    stats.sort_stats(sort)
    stats.print_stats(lines)


@contextlib.contextmanager
def undo(name=None):
    """Gather all the maya commands under the same undo chunk.

    This creates a big block of commands that can be cancelled at once.

    Note:
        Using the maya :func:`cmds.undoInfo` command to create the chunk can be
        dangerous if used incorrectly. If a chunk is opened but never closed
        (e.g. an error occurs during execution), the maya undo list may be
        corrupted, and some features may not work properly.

        This context manager handles this, and ensures that the chunk will
        always be closed, even if the content produces an error.

    Examples:
        First, the default behaviour of Maya. When the undo is performed,
        the last node created is correctly undone, but the first one still
        exists in the scene:

        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> _ = cmds.createNode("transform", name="A")
        >>> _ = cmds.createNode("transform", name="B")
        >>> cmds.undo()
        >>> cmds.objExists("B")
        False
        >>> cmds.objExists("A")
        True

        The cancellation chunk allows a block of commands to be collected
        within the same undo chunk which can be undo at once:

        >>> _ = cmds.file(new=True, force=True)
        >>> with undo(name="create_transform"):
        ...     _ = cmds.createNode("transform", name="A")
        ...     _ = cmds.createNode("transform", name="B")
        >>> cmds.undoInfo(query=True, undoName=True)
        'create_transform'
        >>> cmds.undo()
        >>> cmds.objExists("B")
        False
        >>> cmds.objExists("A")
        False

    Arguments:
        name (str): The name with which the chunk can be identified.
    """
    try:
        cmds.undoInfo(chunkName=name, openChunk=True)
        yield
    finally:
        cmds.undoInfo(chunkName=name, closeChunk=True)


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
        *args: The name of the node to unlock
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
