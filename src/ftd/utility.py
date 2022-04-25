"""Provide utilities to interact with the Autodesk Maya."""
import contextlib
import functools
import logging

from maya import cmds

__all__ = ["exec_string", "keep_selected"]

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
