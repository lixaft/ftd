from __future__ import division

import contextlib
import functools
import math

from maya import cmds, mel
from maya.api import OpenMaya


@contextlib.contextmanager
def lock_node_editor():
    """Prevents adding new nodes in the Node Editor.

    This context manager can be useful when building rigs as adding nodes to
    the editor at creation can be very time consuming when many nodes are
    generated at the same time.
    """
    panel = mel.eval("getCurrentNodeEditor")
    state = cmds.nodeEditor(panel, query=True, addNewNodes=True)
    cmds.nodeEditor(panel, edit=True, addNewNodes=False)
    yield
    cmds.nodeEditor(panel, edit=True, addNewNodes=state)


def create_and_match(func):
    """Improves the way to create nodes."""

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        selection = cmds.ls(selection=True) or [""]

        if "." in selection[0]:
            tool = "Move"
            cmds.setToolTo(tool)
            pos = cmds.manipMoveContext(tool, query=True, position=True)
            ori = cmds.manipMoveContext(tool, query=True, orientAxes=True)

            func_return = func(*args, **kwargs)
            cmds.setAttr(func_return + ".translate", *pos)
            cmds.setAttr(func_return + ".rotate", *map(math.degrees, ori))
            return [func_return]

        list_return = []
        for _, node in enumerate(selection):
            func_return = func(*args, **kwargs)
            if node:
                cmds.matchTransform(func_return, node)
            list_return.append(func_return)

        cmds.select(list_return)
        return list_return

    return _wrapper


def barycentric_coordinates(a, b, c, point):
    # pylint: disable=invalid-name
    """Generate the barycentric coordinates of the given points.

    The barycentric coordinates describe the position of a point contained
    in a triangle by a series of weights corresponding to each point of the
    triangle.

    For a point :math:`P` in a triangle :math:`ABC`, the barycentric
    coordinates of point :math:`P` are represented by the formula:

    .. math::
        P = w_aA + w_bB + w_cC

    Note:
        The sum of the three weights is equal to one:

        .. math::
            1 = w_a + w_b + w_c

    Examples:
        >>> coord = barycentric_coordinates(
        ...     a=(10, 0, 0),
        ...     b=(0, 0, 0),
        ...     c=(0, 0, 10),
        ...     point=(2, 0, 2),
        ... )
        >>> coord
        (0.2, 0.6, 0.2)
        >>> sum(coord)
        1.0

    Arguments:
        a (tuple): The first point of the triangle.
        b (tuple): The second point of the triangle.
        c (tuple): The third point of the triangle.
        point (tuple): The point on which generate the coordinates.

    Returns:
        tuple: The generated coordinates.
    """
    a, b, c, p = map(OpenMaya.MPoint, (a, b, c, point))

    global_area = ((b - a) ^ (c - a)).length()
    coordinates = (
        ((b - p) ^ (c - p)).length() / global_area,
        ((c - p) ^ (a - p)).length() / global_area,
        ((a - p) ^ (b - p)).length() / global_area,
    )
    return coordinates


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
