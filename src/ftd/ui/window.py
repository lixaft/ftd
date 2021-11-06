"""This module provides some class to easly create windows."""
import logging

from maya import OpenMayaUI, cmds
from PySide2 import QtWidgets
from shiboken2 import wrapInstance

import ftd.ui.utility

__all__ = ["Base", "Dockable"]

LOG = logging.getLogger(__name__)


class Base(QtWidgets.QDialog):
    """Base class for creating user interface in maya.

    Arguments:
        parent (QWidget): The widget under which the window will be parented.
    """

    name = "abstract"
    """str: The internal name of the window."""
    title = None
    """str: The name of the window displayed to the user."""

    def __init__(self, parent=None):
        parent = parent or ftd.ui.utility.get_toplevel()
        super(Base, self).__init__(parent)

        self.setObjectName(self.name)
        self.setWindowTitle(self.title or self.name.replace("_", " ").title())
        self.setup()

    def show(self):
        """Show the widget, but first checks if it is not already exists."""
        if self.parent():
            for each in self.parent().children():
                if each.objectName() == self.objectName():
                    each.close()
        super(Base, self).show()

    def setup(self):
        """Setup the widgets of the window."""


class Dockable(Base):
    """Base class to create dockable interfaces in maya."""

    def __init__(self, parent=None):
        self._workspace = "{}_workspaceControl".format(self.name)
        super(Dockable, self).__init__(parent=parent)

        self._panel = None
        self._area = None

    def show(self):
        super(Dockable, self).show()

        # make sur the workspace is not existing.
        if cmds.workspaceControl(self._workspace, query=True, exists=True):
            cmds.deleteUI(self._workspace)

        # create the workspace control
        flags = {}
        flags["label"] = self.windowTitle()
        flags["minimumWidth"] = self.minimumWidth()
        flags["minimumHeight"] = self.minimumHeight()
        if self._panel and self._area:
            flags["dockToControl"] = (self._panel, self._area)

        cmds.workspaceControl(self._workspace)
        cmds.workspaceControl(self._workspace, edit=True, **flags)

        # convert the workspace control into a qt object
        pointer = OpenMayaUI.MQtUtil.findControl(self._workspace)
        to_py = getattr(__builtins__, "long", int)
        workspace = wrapInstance(to_py(pointer), QtWidgets.QWidget)

        # add the instance to the workspace control
        layout = workspace.layout()
        layout.addWidget(self)

    def dock_to(self, panel, area):
        """Dock the control workspace to the given widget."""
        self._panel = panel
        self._area = area
        cmds.workspaceControl(
            self._workspace,
            edit=True,
            dockToControl=[panel, area],
        )

    def close(self):
        """Close the window and the workspace at once."""
        if cmds.workspaceControl(self._workspace, query=True, exists=True):
            cmds.deleteUI(self._workspace)
        super(Dockable, self).close()
