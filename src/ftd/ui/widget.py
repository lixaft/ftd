# pylint: disable=invalid-name
"""Provide pyside2 widgets to use in UI."""
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

    def __init__(self, title, state=True, parent=None):
        super(FrameBox, self).__init__(parent)
        self.setStyleSheet(self.css)

        self.__state = state

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

        self.setState(self.__state)
        self.__button.toggled.connect(self.toggle)

    @property
    def __attached_widget(self):
        """Widget: The attached widget."""
        widget = self.__layout.itemAt(1)
        return widget.wid if widget else None

    def expand(self):
        """Expand the visibility of the attached widget."""
        self.__icon.setIcon(self.open_icon)
        widget = self.__attached_widget
        if widget:
            widget.setVisible(True)
        self.__state = True
        self.toggled.emit(True)

    def shrink(self):
        """Shrink the visibility of the attached widget."""
        self.__icon.setIcon(self.close_icon)
        widget = self.__attached_widget
        if widget:
            widget.setVisible(False)
        self.__state = False
        self.toggled.emit(False)

    def toggle(self):
        """Switch between :meth:`shrink` and :meth:`expand` methods."""
        if self.__state:
            self.shrink()
        else:
            self.expand()

    def setState(self, state):
        """Set the visibility state of the sub-widget."""
        if state:
            self.expand()
        else:
            self.shrink()

    def setWidget(self, widget):
        """Set the sub-widget."""
        self.__layout.takeAt(1)
        self.__layout.addWidget(widget)
        self.setState(self.__state)
