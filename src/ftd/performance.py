"""Provide utilities to measure performance."""
from __future__ import division

import contextlib
import cProfile
import functools
import logging
import pstats
import time

from maya import cmds

__all__ = ["fps", "profile", "timing"]

LOG = logging.getLogger(__name__)


def fps(loop=5, mode="parallel", gpu=True, cache=False, renderer="vp2"):
    # pylint: disable=unused-argument
    """Measure the fps of the current scene.

    It take the active range of the scene, play it view time and show the
    result in the stdout.

    The values for the evulation mode parameter are (the case does not matter):

    ============ ======= ===========================
        Long      Short         Description
    ============ ======= ===========================
    ``parallel`` ``emp`` Evaluation Manager Parallel
    ``serial``   ``ems`` Evaluation Manager Serial
    ``dirty``    ``dg``  Maya evaluation
    ============ ======= ===========================

    The default available renderer are:

    ======================== =======
               Long           Short
    ======================== =======
    ``base_OpenGL_Renderer`` ``vp1``
    ``vp2Renderer``          ``vp2``
    ======================== =======

    Arguments:
        loop (int): The number of times the test should be run.
        mode (str): The evaluation mode to use.
        gpu (bool): Turn on/off the gpu override.
        cache (bool): Turn on/off the cached playback.
        renderer (str): The viewport that will be used to run the test.
    """
    panel = cmds.getPanel(withFocus=True)

    # Set the playback speed to free
    playback_spped = cmds.playbackOptions(query=True, playbackSpeed=True)
    cmds.playbackOptions(edit=True, playbackSpeed=0)

    # Set the viewport renderer
    current_renderer = cmds.modelEditor(panel, query=True, rendererName=True)
    args = {"vp1": "base_OpenGL_Renderer", "vp2": "vp2Renderer"}
    arg = args.get(renderer.lower(), renderer)
    cmds.modelEditor(panel, edit=True, rendererName=arg)

    # Set the evaluation mode
    current_mode = cmds.evaluationManager(query=True, mode=True)[0]
    args = {
        "emp": "parallel",
        "ems": "serial",
        "dg": "off",
        "//": "parallel",
        "->": "off",
    }
    cmds.evaluationManager(mode=args.get(mode.lower(), mode.lower()))

    # Disable cycle check
    cycle_check = cmds.cycleCheck(query=True, evaluation=True)
    cmds.cycleCheck(evaluation=False)

    # Run performance test
    results = []
    current_frame = cmds.currentTime(query=True)
    start_frame = cmds.playbackOptions(query=True, minTime=True)
    end_frame = cmds.playbackOptions(query=True, maxTime=True)
    frame_range = end_frame - start_frame
    for _ in range(loop):
        cmds.currentTime(start_frame)
        start_time = time.time()
        cmds.play(wait=True)
        end_time = time.time()
        result = end_time - start_time
        results.append(round(frame_range / result))
    cmds.currentTime(current_frame)

    # Restore the configuration
    cmds.playbackOptions(edit=True, playbackSpeed=playback_spped)
    cmds.modelEditor(panel, edit=True, rendererName=current_renderer)
    cmds.evaluationManager(mode=current_mode)
    cmds.cycleCheck(evaluation=cycle_check)

    # Display the result
    msg = "PERFORMANCE TEST\n"
    msg += "=" * (len(msg) - 1) + "\n\n"
    for result in results:
        msg += "\t- {} FPS\n".format(result)

    msg += "\n\tMIN: {} FPS".format(min(results))
    msg += "\n\tMAX: {} FPS".format(max(results))
    msg += "\n\n\tAVERAGE: {} FPS".format(round((sum(results) / len(results))))

    LOG.info("\n\n\n%s\n\n\n", msg)


@contextlib.contextmanager
def profile(sort="time", lines=None, strip=False):

    """Detail the execution of all statements in the block.

    The following are the values accepted by the ``sort`` parameter:

    ================= ======================
          Value            Description
    ================= ======================
    ``calls``         Call count
    ``cumulative``    Cumulative time
    ``filename``      File name
    ``pcalls``        Primitive call count
    ``line``          Line number
    ``name``          Function name
    ``nfl``           Name/file/line
    ``stdname``       Standard name
    ``time``          Internal time
    ================= ======================

    Arguments:
        sort (str): Sorts the output according to the specified mode.
        lines (int): Limits the output to a specified number of lines.
        strip (bool): Removes all leading path information from file name.
    """
    profiler = cProfile.Profile()
    try:
        profiler.enable()
        yield
    finally:
        profiler.disable()

    stats = pstats.Stats(profiler)
    if strip:
        stats.strip_dirs()
    stats.sort_stats(sort)
    stats.print_stats(lines)


def timing(unit="millisecond", message="{func.__name__}() {time:.3f} {unit}"):
    """Measures the execution time of the function.

    The value that can be used for specified the ``unit`` parameter are:

    ======== ================= ==================
      Short        Long             Length
    ======== ================= ==================
    ``m``    ``minute``        60s
    ``s``    ``second``        1s
    ``ms``   ``millisecond``   10\\ :sup:`-3`\\ s
    ``us``   ``microsecond``   10\\ :sup:`-6`\\ s
    ``ns``   ``nanosecond``    10\\ :sup:`-9`\\ s
    ======== ================= ==================

    The ``message`` parameter can be formatted using the following fields:

    ========= =============================
       Name            Description
    ========= =============================
    ``func``  The instance of the function.
    ``time``  The execution time.
    ``unit``  The time unit.
    ========= =============================

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
