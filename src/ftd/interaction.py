"""Provide utilities to interact with the Autodesk Maya."""
import contextlib
import functools
import logging

from maya import cmds

__all__ = ["keep_selected", "repeat", "undo", "undo_chunk", "undo_repeat"]

LOG = logging.getLogger(__name__)


def keep_selected(func):
    """Keep the selection unchanged after the execution of the function."""

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        sel = cmds.ls(selection=True)
        returned = func(*args, **kwargs)
        if sel:
            cmds.select(sel)
        else:
            cmds.select(clear=True)
        return returned

    return _wrapper


def repeat(func):
    """Decorate a function to make it repeatable.

    This means that in maya, when the shortcut ``ctrl+G`` is triggered,
    the decorate function will be executed again.
    """

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        # store a partial version on the module variables so that it
        # can be executed later when the repeat action will be triggered
        globals()["_callback"] = functools.partial(func, *args, **kwargs)

        # find the code to execute to call the function previously stored
        command = "_callback()"
        if __name__ != "__main__":
            command = "import {0};{0}.{1}".format(__name__, command)

        # add the function to the repeat system of maya
        cmds.repeatLast(
            addCommandLabel="{f.__module__}.{f.__name__}".format(f=func),
            # the `addCommand` flag only accepts mel commands
            addCommand='python("{}")'.format(command),
        )
        return func(*args, **kwargs)

    return _wrapper


def undo(func):
    """The decorator version of the context manager :func:`ftd.context.undo`.

    The chunk will be named by the python path of the function
    e.g. ``ftd.interaction.undo``.

    See the context manager documentation for more information.
    """

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        with undo_chunk("{f.__module__}.{f.__name__}".format(f=func)):
            return func(*args, **kwargs)

    return _wrapper


@contextlib.contextmanager
def undo_chunk(name=None):
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
        >>> with undo_chunk(name="create_transform"):
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


def undo_repeat(func):
    """Combine :func:`undo` and :func:`repeat` decorators."""
    return repeat(undo(func))
