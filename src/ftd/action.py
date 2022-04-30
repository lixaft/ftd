# type: ignore
"""Command that can be stored and executed."""
import importlib
import re

import yaml

ACTIONS = {}
DECORATORS = {}


def execute(action):
    """Execute the given action."""
    tokens = action.split("@")
    act = ACTIONS.get(tokens.pop(0))
    if act is None:
        raise ValueError("No action named '{}'.".format(action))
    return act.execute(*tokens)


class Action(object):
    """A command that can be executed."""

    _FUNCTION = "main"
    _EXPORTED = [
        "name",
        "description",
        "icon",
        "tags",
        "long",
        "nice",
        "short",
        "decorators",
        "code",
        "variants",
    ]

    def __repr__(self):
        return "<Action '{}'>".format(self.identifier)

    def __init__(self, identifier):
        self.identifier = identifier
        normalized = re.sub(r"(?<!^)([A-Z])", r" \1", identifier)
        self.name = re.sub(r"\W", "_", normalized).lower()

        self.description = ""
        self.icon = ["commandButton.png"]
        self.tags = []

        self.long = self.name.replace("_", " ").strip()
        self.nice = self.long.title()
        self.short = "".join(x[0] for x in self.long.split())

        self.decorators = []
        self.code = ""

        self.variants = []

    def build_function(self, variant=None, module=False):
        """Convert the code into a string function."""
        lines = []

        name = self.identifier
        code = self.code
        if variant is not None:
            data = self.get_variant_data(variant)
            code = data.get("code", "")
            name += "@{}".format(data.get("name", ""))

        if module:
            lines_ = [
                '"""Action for `{}`."""'.format(name),
                "",
            ]
            lines.extend(lines_)

        lines_ = ["def {}():\n", '"""{}"""\n'] + code.splitlines(True)
        func = (" " * 4).join(lines_).format(self._FUNCTION, self.description)
        lines.append(func)

        if module:
            lines_ = [
                'if __name__ == "__main__":',
                "    {}()".format(self._FUNCTION),
            ]
            lines.extend(lines_)

        return "\n".join(lines)

    def build_callable(self, variant=None):
        """Build a callable function."""
        # pylint: disable=exec-used
        exec(self.build_function(variant))
        cmd = locals()[self._FUNCTION]
        for decorator in self.decorators:
            cmd = DECORATORS[decorator](cmd)
        return cmd

    def execute(self, variant=None):
        """Execute the command."""
        return self.build_callable(variant)()

    def get_variant_data(self, name):
        """Get the variant data."""
        for variant in self.variants:
            if variant.get("name") == name:
                return variant
        raise NameError("Unknown variant")

    def to_dict(self):
        """Convert the action to a python dictionary."""
        return {x: getattr(self, x) for x in self._EXPORTED}

    @classmethod
    def from_dict(cls, identifier, config):
        """Build an action object from the action dictionary."""
        action = cls(identifier)
        for key, value in config.items():
            if key in cls._EXPORTED:
                setattr(action, key, value)
        return action


def load_actions_from_file(path):
    """Register the actions from a given YAML file."""
    with open(path, "r") as stream:
        actions = yaml.load(stream, Loader=yaml.FullLoader)

    for identifier, config in actions.items():
        action = Action.from_dict(identifier, config or {})
        ACTIONS[identifier] = action


def load_decorators_from_file(path):
    """Tg."""
    with open(path, "r") as stream:
        decorators = yaml.load(stream, Loader=yaml.FullLoader)

    for identifier, path in decorators.items():
        mod, func_name = path.rsplit(".", 1)
        decorator = getattr(importlib.import_module(mod), func_name)
        DECORATORS[identifier] = decorator
