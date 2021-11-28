# pylint: disable=invalid-name, no-self-use
"""This module provides utilities for common tasks involving layouts.

:author: Fabien TAXIL <fabien.taxil@gmail.com>
"""
import logging

from PySide2 import QtCore, QtWidgets

__all__ = ["Flow"]


LOG = logging.getLogger(__name__)


class Flow(QtWidgets.QLayout):
    """A layout that arranges the widgets according to the window size.

    Based on the `Qt C++ example`_.

    .. _Qt C++ example:
        https://doc.qt.io/qtforpython/overviews/qtwidgets-layouts-flowlayout-example.html
    """

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def __init__(self, parent=None, margin=0, spacing=0):
        super(Flow, self).__init__(parent=parent)

        self.setMargin(margin)
        self.setSpacing(spacing)
        self.item_list = []

    def addItem(self, item):
        """Reimplemented the :func:`addItem` method."""
        self.item_list.append(item)

    def count(self):
        """Reimplemented the :func:`count` method."""
        return len(self.item_list)

    def itemAt(self, index):
        """Reimplemented the :func:`itemAt` method."""
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index):
        """Reimplemented the :func:`takeAt` method."""
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None

    def expandingDirections(self):
        """Reimplemented the :func:`expandingDirections` method."""
        return QtCore.Qt.Orientations(QtCore.Qt.Orientation(0))

    def hasHeightForWidth(self):
        """Reimplemented the :func:`hasHeightForWidth` method."""
        return True

    def heightForWidth(self, width):
        """Reimplemented the :func:`heightForWidth` method."""
        height = self.doLayout(QtCore.QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        """Reimplemented the :func:`setGeometry` method."""
        super(Flow, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        """Reimplemented the :func:`sizeHint` method."""
        return self.minimumSize()

    def minimumSize(self):
        """Reimplemented the :func:`minimumSize` method."""
        size = QtCore.QSize(0, 0)
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()
        size += QtCore.QSize(
            margins.left() + margins.right(), margins.top() + margins.bottom()
        )
        return size

    def doLayout(self, rect, test_only):
        """Update the item position.

        Arguments:
            rect (QRect): The available space.
            test_only (bool): Apply the changes or not.

        Returns:
            int: The height needed to display all items.
        """
        left, top, right, bottom = self.getContentsMargins()
        x, y = left, top
        line_height = 0

        for item in self.item_list:
            # check if the current object can fit
            # if not, go to the next line
            next_x = x + item.sizeHint().width() + right
            if next_x > rect.right() and line_height:
                x = left
                y += self.spacing() + line_height
                line_height = 0

            # set the item position
            if not test_only:
                item.setGeometry(
                    QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint())
                )

            # update values with the current item for next iteration
            x += item.sizeHint().width() + self.spacing()
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height + bottom
