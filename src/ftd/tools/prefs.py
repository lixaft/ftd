"""Maya preferences management based on serialized files."""
import importlib
import json
import logging
import os

import six
import yaml
from maya import cmds

LOG = logging.getLogger(__name__)

ENVIRON = os.getenv("FTD_PREFS", None)
"""str: File paths where configuration files can be found.

All files in these directories will be automatically loaded when the module is
initialised.
"""
LOCAL = os.path.join(os.path.dirname(__file__), "..", "configs", "prefs.yaml")
"""str: The package internal configuration file."""


def initialize():
    """Initialize the maya preferences from the default paths.

    See :obj:`ENVIRON` and :obj:`LOCAL`.
    """
    load_file(os.path.abspath(LOCAL))

    if not ENVIRON:
        return

    for directory in ENVIRON.split(os.pathsep):
        if not os.path.exists(directory):
            continue
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            _, ext = os.path.splitext(name)
            if ext not in (".yaml", ".json"):
                continue
            load_file(path)


def load_file(path):
    """Load all the content of a serialized file and dispatch it into the api.

    Arguments:
        path (str): The path of the serialized file to load.
    """
    filedata = _unserialize(path)

    # commands
    for name, kwargs in filedata.get("commands", {}).items():
        Command(name, **kwargs)

    # decorators
    for name, decorator in filedata.get("decorators", {}).items():
        Command.register_decorator(name, decorator)

    # hotkeys
    for name, data in filedata.get("hotkey_sets", {}).items():
        create_hotkey_set(
            name=name,
            base=data.get("base"),
            hotkeys=data.get("hotkeys", []),
        )

    # marking menus
    for name, data in filedata.get("marking_menus", {}).items():
        create_marking_menu(
            name=name,
            key=data["key"],
            items=data["items"],
            parent=data.get("parent"),
        )

    # colors
    for key, value in filedata.get("colors", {}).items():
        if isinstance(value, int):
            cmds.displayColor(key, value)
        elif isinstance(value, list):
            cmds.displayRGBColor(key, *value)

    # options
    for key, value in filedata.get("options", {}).items():
        if isinstance(value, (int, bool)):
            cmds.optionVar(intValue=(key, int(value)))
        elif isinstance(value, six.string_types):
            cmds.optionVar(stringValue=(key, value))


# Utilities
def _unserialize(path):
    """Unserialize a file to an python object.

    The JSON a YAML format are currently supported.
    """
    _, ext = os.path.splitext(path)

    with open(path, "r") as stream:

        if ext == ".json":
            return json.load(stream)
        if ext in (".yaml", ".yml"):
            return yaml.load(stream, Loader=yaml.FullLoader)

    raise TypeError("Invalid file extension '{}'.".format(ext))


def run_command(name):
    """Run a command base on its name."""
    Command.get(name).execute()


# Core
class Command(object):
    """A command that can be executed."""

    _registered = {}
    _decorators = {}

    def __init__(self, name, core, decorators=None, description=""):
        self._name = name
        self._core = core
        self._description = description
        self._used_decorators = decorators or []

        self._registered[name] = self

    # Read properties ---
    @property
    def name(self):
        """str: The name of the command."""
        return self._name

    @property
    def core(self):
        """str: The python code executed by the command."""
        return self._core

    @property
    def decorators(self):
        """list: The decorators that will be applied to the command."""
        return self._used_decorators

    @property
    def description(self):
        """str: A short text that describes the command."""
        return self._description

    # Public methods ---
    def execute(self):
        """Execute the command."""
        return self.build_callable()()

    def build_string(self):
        """Get a string that can be executed via :func:`exec`."""
        # prepare the decorators
        import_lines = set()
        decorator_lines = []
        for each in self._used_decorators:
            obj = self._decorators[each]
            import_lines.add("import " + obj.__module__)
            decorator_lines.append(
                "@{}.{}".format(obj.__module__, obj.__name__)
            )
        # build the string
        string = '"""{}"""\n'.format(self._description)
        string += "\n".join(list(import_lines) + [""] + decorator_lines) + "\n"
        string += self._build_function(self._core, self._name)
        string += '\nif __name__ == "__main__":\n    {}()\n'.format(self._name)
        return string

    def build_callable(self):
        """Build a callable function."""
        # pylint: disable=exec-used
        exec(self._build_function(self._core, self._name))
        cmd = locals()[self._name]
        for decorator in self._used_decorators:
            cmd = self._decorators[decorator](cmd)
        return cmd

    # Class methods ---
    @classmethod
    def from_dict(cls, dictionary):
        """Create an instance of :class:`Command` from a dictionary."""
        return cls(**dictionary)

    @classmethod
    def get(cls, key):
        """Get a registered command."""
        return cls._registered[key]

    @classmethod
    def get_decorator(cls, key):
        """Get a decorator stored in the class."""
        return cls._decorators.get(key)

    @classmethod
    def register_decorator(cls, name, decorator):
        """Register a decorator to make it available via its name."""
        if isinstance(decorator, str):
            mod, name = decorator.rsplit(".", 1)
            decorator = getattr(importlib.import_module(mod), name)
        cls._decorators[name] = decorator

    # Private methods ---
    @staticmethod
    def _build_function(core, name="_command"):
        func = (" " * 4).join(["def {}():\n"] + core.splitlines(True))
        return func.format(name)


def create_hotkey_set(name, hotkeys, base="Maya_Default"):
    """Create an hotkey set based on the given data.

    Arguments:
        name (str): The name of the hotkey set.
        base (str): The hotkey from which this one will be create.
        hotkeys (list): The list of hotkey to create.
    """
    # create the set
    if cmds.hotkeySet(name, exists=True):
        cmds.hotkeySet(name, edit=True, delete=True)
    cmds.hotkeySet(name, source=base)
    cmds.hotkeySet(name, edit=True, current=True)

    for data in hotkeys:
        cmd = Command.get(data["command"])

        # first, create a `runTimeCommand` which contains the script to be
        # executed and which can be invoked by typing the specified name
        # into the mel interpreter
        cmds.runTimeCommand(
            cmd.name,
            command=cmd.build_string(),
            commandLanguage="python",
            category=data.get("category"),
            edit=cmds.runTimeCommand(cmd.name, query=True, exists=True),
        )

        # then create a `nameCommand` which can be attached to a hotkey to
        # execute the specified `runTimeCommand`
        cmds.nameCommand(
            cmd.name + "_userCommand",
            command=cmd.name,
            annotation=cmd.description or " ",
        )

        # parse the key sequence
        flags = {}
        for key in data["key"].split("+"):
            if key in ("ctrl", "alt", "shift"):
                flags[key + "Modifier"] = True
            else:
                flags["keyShortcut"] = key

        # finally, create the shortcut that will be triggered each time the
        # key sequence is used
        cmds.hotkey(name=cmd.name + "_userCommand", **flags)


def create_marking_menu(name, key, items, parent="MainPane"):
    """Create a marking menu."""
    if cmds.popupMenu(name, exists=True):
        cmds.deleteUI(name)

    # find the menus hotkey
    flags = {}
    for key_ in ("ctrl", "alt", "shift"):
        flags[key_ + "Modifier"] = key_ in key
    for index, btn in enumerate(("left", "middle", "right"), start=1):
        if btn in key:
            flags["button"] = index

    def build_item(data, parent):
        flags = {}
        if "position" in data:
            flags["radialPosition"] = data["position"].upper()

        if "menu" in data:
            flags["subMenu"] = True
            flags["label"] = data["name"]

        elif "divider" in data:
            flags["divider"] = True

        else:
            cmd = Command.get(data["main"])
            flags["label"] = cmd.name
            flags["command"] = lambda _: cmd.execute()

        item = cmds.menuItem(parent=parent, **flags)
        # children
        if "option" in data:
            cmd = Command.get(data["option"])
            cmds.menuItem(
                command=lambda _: cmd.execute(),
                optionBox=True,
                parent=parent,
            )
        elif "menu" in data:
            for each in data["items"]:
                build_item(each, item)

    def main_build(name, _):
        cmds.popupMenu(name, edit=True, deleteAllItems=True)
        for item in items:
            build_item(item, name)

    cmds.popupMenu(
        name,
        markingMenu=True,
        allowOptionBoxes=True,
        parent=parent,
        postMenuCommand=main_build,
        # postMenuCommandOnce=True,
        **flags,
    )