# pylint: disable=invalid-name
"""This module provides utilities for common tasks involving widgets.

:author: Fabien Taxil <fabien.taxil@gmail.com>
"""
import logging

from PySide2 import QtCore, QtGui, QtWidgets

import ftd.ui.utility

__all__ = ["IconButton", "FrameBox"]

LOG = logging.getLogger(__name__)


class IconButton(QtWidgets.QToolButton):
    """A custom pyside2 button to use with icon."""

    css = """
        QToolButton {
            border: none;
        }
    """

    def __init__(self, icon=None, parent=None):
        super(IconButton, self).__init__(parent)

        self.__menu = {}

        self.setStyleSheet(self.css)
        self.setAutoRaise(True)
        if icon:
            self.setIcon(icon)

    def setMenu(self, menu, click=QtCore.Qt.MouseButton.RightButton):
        """Reimplemented the :func:`setMenu` method.

        Arguments:
            menu (QtWidgets.QMenu): The menu to be attached to the button.
            click (QtCore.Qt.QMouseButton): The click to use to show the menu.
        """
        if not isinstance(menu, QtWidgets.QMenu):
            LOG.error("Wrong data type. Must be a <QtWidgets.QMenu>.")
            return
        if not isinstance(click, QtCore.Qt.MouseButton):
            LOG.error("Wrong data type. Must be a <QtCore.Qt.QMouseButton>.")
            return
        self.__menu[click] = menu

    def menu(self, click):
        """Reimplemented the :func:`menu` method."""
        return self.__menu[click]

    def mousePressEvent(self, event):
        """Reimplemented the :func:`mousePressEvent` method."""
        super(IconButton, self).mousePressEvent(event)
        for click, menu in self.__menu.items():
            if event.button() == click:
                pos = QtGui.QCursor().pos()
                menu.exec_(pos)
                self.update()

    def setIcon(self, icon):
        """Reimplemented the :func:`setIcon` method."""
        if isinstance(icon, str):
            icon = ftd.ui.utility.find_icon(icon)
        super(IconButton, self).setIcon(icon)


class FrameBox(QtWidgets.QWidget):
    """Custom expandable widget."""

    toggled = QtCore.Signal(bool)

    css = """
        QPushButton#header {
            color: rgb(189, 189, 189);
            background-color: rgb(93, 93, 93);
            border: none;
            padding: 5px;
            padding-left: 25px;
            font: bold;
            text-align: left;
            border-radius: 2px;
        }
    """

    open_icon = ftd.ui.utility.find_icon("framebox/open.svg", qt=True)
    close_icon = ftd.ui.utility.find_icon("framebox/close.svg", qt=True)

    def __init__(self, title, parent=None):
        super(FrameBox, self).__init__(parent)
        self.setStyleSheet(self.css)

        self.__button = QtWidgets.QPushButton(title)
        self.__button.setCheckable(True)
        self.__button.setObjectName("header")

        self.__icon = QtWidgets.QToolButton(self.__button)
        self.__icon.setFixedSize(QtCore.QSize(20, 20))
        self.__icon.setStyleSheet("border: none;")
        self.__icon.setIconSize(QtCore.QSize(11, 11))
        self.__icon.setIcon(self.close_icon)
        self.__icon.mousePressEvent = self.__button.mousePressEvent

        self.__layout = QtWidgets.QVBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(0)
        self.__layout.addWidget(self.__button)

        self.__button.toggled.connect(self.setState)

    def setState(self, state):
        """Set the visibility state of the sub-widget."""
        widget = self.__layout.itemAt(1)
        if widget:
            widget.wid.setVisible(state)
        self.__icon.setIcon(self.open_icon if state else self.close_icon)
        self.toggled.emit(state)

    def setWidget(self, widget):
        """Set the sub-widget."""
        self.__layout.takeAt(1)
        self.__layout.addWidget(widget)
        self.setState(self.__button.isChecked())
