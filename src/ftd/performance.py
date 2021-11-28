"""Provide utilities to measure performance."""
import contextlib
import cProfile
import functools
import logging
import pstats
import time

__all__ = ["profile", "timing"]

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
