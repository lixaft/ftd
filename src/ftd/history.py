"""Utilities related to history."""
import contextlib
import functools
import logging
import sys
import trace

from maya import cmds

__all__ = ["repeat", "undo", "undo_chunk", "undo_repeat", "traceit"]

LOG = logging.getLogger(__name__)


def repeat(func):
    """Decorate a function to make it repeatable.

    This means that in maya, when the shortcut ``ctrl+G`` is triggered,
    the decorate function will be executed again.
    """

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        # Store a partial version on the module variables so that it
        # can be executed later when the repeat action will be triggered.
        globals()["_callback"] = functools.partial(func, *args, **kwargs)

        # find the code to execute to call the function previously stored
        command = "_callback()"
        if __name__ != "__main__":
            command = "import {0};{0}.{1}".format(__name__, command)

        # Ddd the function to the repeat system of maya
        cmds.repeatLast(
            addCommandLabel="{f.__module__}.{f.__name__}".format(f=func),
            # The `addCommand` flag only accepts mel code :/
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


def undo_repeat(func):
    """Combine :func:`undo` and :func:`repeat` decorators."""
    return repeat(undo(func))


@contextlib.contextmanager
def undo_chunk(name=None):
    """Gather all the maya commands under the same undo chunk.

    Using the maya :func:`cmds.undoInfo` command to create the chunk can be
    dangerous if used incorrectly. If a chunk is opened but never closed
    (e.g. an error occurs during execution), the maya undo list may be
    corrupted, and some features may not work properly.

    This context manager will handle the issue and like the :func:`open`
    function, will ensure that the chunk is properly close whatever happen
    during the execution of the body.

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

        The undo chunk allows a block of commands to be collected within
        the same undo chunk which can be undo at once:

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


def traceit(func, path):
    """Trace the execution of the given function and make a report.

    Arguments:
        func (function): The function to execute and trace.
        path (str): The filepath where the report will be saved.
    """
    stdin = sys.stdin
    stdout = sys.stdout

    with open(path, "w") as stream:
        sys.stdin = stream
        sys.stdout = stream

        try:
            tracer = trace.Trace(count=False, trace=True)
            tracer.runfunc(func)
        finally:
            sys.stdin = stdin
            sys.stdout = stdout
