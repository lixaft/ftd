"""This module provides utilities for common tasks involving user interface."""
import inspect
import logging
import os

from PySide2 import QtCore, QtGui, QtWidgets

__all__ = ["find_icon", "get_toplevel"]

LOG = logging.getLogger(__name__)


def find_icon(name, default=None, directory="icons", qt=False, limit=5):
    # pylint: disable=invalid-name
    """Search a file in related icons directory.

    Examples:
        >>> find_icon("commandButton.png")
        ':/commandButton.png'
        >>> icon = find_icon("commandButton.png", qt=True)
        >>> type(icon)
        <class 'PySide2.QtGui.QIcon'>

    Arguments:
        name (str): The name of the file to found.
        default (str): The icon name used if the first name is not found.
        directory (str): The name of the directory to be inspected.
        qt (bool): If True, return a PySide2 icon instance.
        limit (int): The depth limit of the search.

    Returns:
        str | QIcon: The absolute path where the icon was found or an instance
            of QIcon if ``qt`` parameter is set to ``True``.
    """
    for frame in reversed(inspect.stack()[0:limit]):
        icon = os.path.join(os.path.dirname(frame[1]), directory, name)
        if os.path.exists(icon):
            break
    else:
        if not os.path.exists(icon):
            icon = ":/{}".format(name)

        if not QtCore.QFile.exists(icon):
            icon = find_icon(default) if default else ""

    if not icon:
        LOG.warning("No icon found for '%s'", name)
    return QtGui.QIcon(icon) if qt else icon


def get_toplevel(name="MayaWindow"):
    """Find a top level widget with a specified name.

    Arguments:
        name (str): The widget name to search.

    Returns:
        QWidget: The top level widget.
    """
    widget = QtWidgets.QApplication.topLevelWidgets()
    return ([x for x in widget if x.objectName() == name] or [None])[0]
