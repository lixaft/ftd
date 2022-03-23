"""Provide utilities to interact with the Autodesk Maya."""
import contextlib
import functools
import logging
import sys
import trace

from maya import cmds

__all__ = [
    "exec_string",
    "keep_selected",
    "repeat",
    "traceit",
    "undo",
    "undo_chunk",
    "undo_repeat",
]

LOG = logging.getLogger(__name__)


def exec_string(string, language="python", decorators=None):
    """Execute a string as python code.

    The languages available are ``python`` and ``mel``.

    During the process, creates a new function and calls it using the
    :func:`exec` builtin function.

    With this process, it is possible to apply decorators to the string to be
    executed. Even if the language is set to "python" or "mel", because in the
    case where the string is written in "mel", a python function is still
    created and called the :func:`mel.eval` command.

    Also, like any python function, it can have a :obj:`return` statement.
    If specified in the string to be executed, the value will be returned.
    See the examples for more details.

    Warning:
        The :obj:`return` statement only works for the python language.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> command = \"\"\"
        ... from maya import cmds
        ... return cmds.polyCube(name="pythonCube")[0]
        ... \"\"\"
        >>> exec_string(command)
        'pythonCube'
        >>> cmds.objExists("pythonCube")
        True

        >>> command = \"\"\"
        ... polyCube -name "melCube";
        ... \"\"\"
        >>> exec_string(command, language="mel")
        >>> cmds.objExists("melCube")
        True

    Arguments:
        string (str): The command to execute as string.
        language (str, optional): The language in which the object provided in
        the ``string`` parameter is written.
        decorators (list, optional): The python decorators to apply at runtime.

    Returns:
        any: Anything that the string will return.

    Raises:
        ValueError: The specified language is not supported by the function.
    """
    lines = ["def _callback():\n"]

    if language == "python":
        lines.extend(string.splitlines(True))
    elif language == "mel":
        line = "from maya import mel;mel.eval('{}')"
        lines.append(line.format(string.replace("\n", "")))
    else:
        msg = "The language '{}' is not supported.".format(language)
        raise ValueError(msg)

    exec((" " * 4).join(lines))  # pylint: disable=exec-used
    callback = locals()["_callback"]

    for decorator in decorators or []:
        try:
            callback = decorator()(callback)
        except TypeError:
            callback = decorator(callback)

    return callback()


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


@contextlib.contextmanager
def restore_nodes(nodes):
    """Restore the nodes before the action."""
    for node in nodes:
        cmds.nodePreset(save=(node, node))
    yield
    for node in nodes:
        cmds.nodePreset(load=(node, node))
        cmds.nodePreset(delete=(node, node))


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
