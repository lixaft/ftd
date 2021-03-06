"""Create a toolbar windows."""
import logging
from functools import partial

import yaml
from PySide2 import QtCore, QtWidgets

import ftd.tools.prefs
import ftd.ui.layout
import ftd.ui.widget
import ftd.ui.window

__all__ = ["show", "Window"]

LOG = logging.getLogger(__name__)


def show(path):
    """Show the marking menu."""
    widget = Window(path)
    widget.show()
    widget.dock_to("Outliner", "left")
    return widget


class Window(ftd.ui.window.Dockable):
    """Main window for the toolbar."""

    name = "toolbar"

    def __init__(self, path):
        super(Window, self).__init__()
        self._config = path
        self.populate()

    def setup(self):
        self.setMinimumWidth(137)

        # Widget
        widgets = {
            "tab": QtWidgets.QTabWidget(),
            "tabs_menu": QtWidgets.QMenu(),
            "tabs": ftd.ui.widget.IconButton(),
            "reload": ftd.ui.widget.IconButton(),
            "settings": ftd.ui.widget.IconButton(),
        }

        # Header icons
        for key in ("tabs", "reload", "settings"):
            icon = ftd.ui.utility.find_icon(key + ".svg", qt=True)
            widgets[key].setIcon(icon)
            widgets[key].setIconSize(QtCore.QSize(17, 17))

        button = QtCore.Qt.MouseButton.LeftButton
        widgets["tabs"].setMenu(widgets["tabs_menu"], button)

        widgets["reload"].clicked.connect(self.populate)

        self.widgets = widgets

        # Layout
        layouts = {
            "main": QtWidgets.QVBoxLayout(self),
            "header": QtWidgets.QHBoxLayout(),
        }

        layouts["header"].setContentsMargins(5, 5, 5, 5)
        layouts["header"].setSpacing(5)
        layouts["header"].addWidget(widgets["tabs"])
        layouts["header"].addStretch()
        layouts["header"].addWidget(widgets["reload"])
        layouts["header"].addWidget(widgets["settings"])

        layouts["main"].setContentsMargins(0, 0, 0, 0)
        layouts["main"].setSpacing(0)
        layouts["main"].addLayout(layouts["header"])
        layouts["main"].addWidget(widgets["tab"])

    def populate(self):
        """Populate the toolbar with the registered tabs."""
        self.widgets["tab"].clear()
        self.widgets["tabs_menu"].clear()

        with open(self._config, "r") as stream:
            config = yaml.load(stream, Loader=yaml.FullLoader)

        ftd.tools.prefs.load_commands(config)
        for tab, data in config["toolbar"].items():
            widget = Tab(data)
            action = partial(self.widgets["tab"].setCurrentWidget, widget)
            self.widgets["tab"].addTab(widget, tab)
            self.widgets["tabs_menu"].addAction(tab, action)


class Tab(QtWidgets.QScrollArea):
    """Custom QScrollArea for the toolbar tabs."""

    def __init__(self, data, parent=None):
        super(Tab, self).__init__(parent=parent)
        self.data = data

        self.setWidgetResizable(True)
        self.setStyle(QtWidgets.QStyleFactory.create("fusion"))

        widget = QtWidgets.QWidget()
        self.setWidget(widget)

        self._layout = QtWidgets.QVBoxLayout(widget)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.populate()
        self._layout.addStretch()

    def populate(self):
        """Populate the widget."""
        for data in self.data:
            widget = Category(data["name"], data)
            self._layout.addWidget(widget)


class Category(ftd.ui.widget.FrameBox):
    """Custom widget for the toolbar categories."""

    def __init__(self, title, data, parent=None):
        super(Category, self).__init__(title, parent=parent)
        self.data = data

        widget = QtWidgets.QWidget()
        self.setWidget(widget)
        self._layout = ftd.ui.layout.Flow()
        widget.setLayout(self._layout)
        self._layout.setContentsMargins(1, 5, 1, 5)
        self._layout.setSpacing(1)

        self.populate()
        self.setState(data.get("visible", True))

    def populate(self):
        """Populate the widget."""
        for data in self.data["children"]:
            widget = Command(data)
            self._layout.addWidget(widget)


class Command(ftd.ui.widget.IconButton):
    """Custom widget for toolbar button."""

    css2 = """
        QLabel {
            background-color: rgba(0, 0, 0, 0.5);
            color: rgba(255, 255, 255, 0.8);
            font-size: 10px;
            border-radius: 3px;
        }
    """

    def __init__(self, data, parent=None):
        super(Command, self).__init__(parent=parent)
        cmd = ftd.tools.prefs.Command.get(data["command"])

        self.setStyleSheet(self.css + self.css2)
        self.setToolTip(cmd.description or cmd.name)
        self.clicked.connect(cmd.execute)

        # Icon
        icon = ftd.ui.utility.find_icon(
            cmd.icon or "commandButton.png", qt=True
        )
        self.setIcon(icon)
        size = QtCore.QSize(38, 38)
        self.setMinimumSize(size)
        self.setMaximumSize(size)
        self.setIconSize(size * 0.9)

        # Text
        if data.get("label"):
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            label = QtWidgets.QLabel(cmd.short)
            label.setAlignment(QtCore.Qt.AlignCenter)
            layout.addStretch()
            layout.addWidget(label)

        # Menu
        menu = QtWidgets.QMenu()
        self.setMenu(menu)
        for option in data.get("options", {}):
            if "divider" in option:
                menu.addSeparator()
                continue
            cmd_ = ftd.tools.prefs.Command.get(option["command"])
            name = "options" if "options" in cmd_.tags else cmd_.long
            menu.addAction(name, cmd_.execute)
