"""Provide utilities for tasks unrelated to maya."""
import logging
import sys
import trace

LOG = logging.getLogger(__name__)

__all__ = ["exec_string", "traceit"]


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
