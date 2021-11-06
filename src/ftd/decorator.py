"""This module provides utility decorators."""
import functools
import logging
import time

from maya import cmds

import ftd.context

__all__ = [
    "undo",
    "repeat",
    "undo_repeat",
    "timing",
    "keep_selected",
]

LOG = logging.getLogger(__name__)


def undo(func):
    """The decorator version of the context manager :func:`ftd.context.undo`.

    The chunk will be named by the python path of the function
    e.g. ``ftd.decorator.undo``.

    See the context manager documentation for more information.
    """

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        with ftd.context.undo("{f.__module__}.{f.__name__}".format(f=func)):
            return func(*args, **kwargs)

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


def undo_repeat(func):
    """Combine :func:`undo` and :func:`repeat` decorators."""
    return repeat(undo(func))


def timing(unit="millisecond", message="{func.__name__}() {time:.3f} {unit}"):
    """Measures the execution time of the function.

    The value that can be used for specified the ``unit`` parameter are:

    .. csv-table::
        :header: Short, Long, Length
        :widths: 20, 30, 20

        ``m``,   ``minute``,       60s
        ``s``,   ``second``,       1s
        ``ms``,  ``millisecond``,  10\\ :sup:`-3`\\ s
        ``us``,  ``microsecond``,  10\\ :sup:`-6`\\ s
        ``ns``,  ``nanosecond``,   10\\ :sup:`-9`\\ s

    The ``message`` parameter can be formatted using the following fields:

    .. csv-table::
        :header: Name, Description
        :widths: 30, 120

        ``func``, The instance of the function.
        ``time``, The execution time.
        ``unit``, The time unit.

    Arguments:
        unit (str):  The unit of time in which the execution time is displayed.
        message (str): The output message displayed after execution.
    """

    def _decorator(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            start = time.time()
            returned = func(*args, **kwargs)
            end = time.time()

            units = {
                "m": 1 / 60,
                "s": 1,
                "ms": 1e3,
                "us": 1e6,
                "ns": 1e9,
                "minute": 1 / 60,
                "second": 1,
                "millisecond": 1e3,
                "microsecond": 1e6,
                "nanosecond": 1e9,
            }
            exec_time = (end - start) * units[unit]
            LOG.info(message.format(func=func, time=exec_time, unit=unit))

            return returned

        return _wrapper

    return _decorator


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
