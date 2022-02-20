# pylint: disable=protected-access
"""Custom sphinx extension to generate API documentation."""
import importlib
import inspect
import os
import pkgutil
import shutil
import sys
import types

import jinja2.sandbox
import sphinx
import sphinx.jinja2glue

__all__ = ["main"]
__version__ = "0.1.0"

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

CONFIG_NAME = __name__ + "_config"
CONFIG_DEFAULT = {
    "filter": r"[a-zA-Z0-9]+",
}


def import_module(module, app):
    """Import a python module."""
    with sphinx.ext.autodoc.mock(app.config.autodoc_mock_imports or []):
        return importlib.import_module(module)


class Node(object):
    """Generic node object."""

    type = ""
    directive = ""

    def __init__(self, name, parent, app):
        prefix = (parent.path + ".") if parent is not None else ""

        self._app = app

        self.name = name
        self.path = prefix + self.name
        self.parent = parent
        self.members = []

        if parent is not None:
            parent.members.append(self)

    @property
    def is_empty(self):
        """bool: True if there is not child members."""
        return bool(self.members)


class Variable(Node):
    """Variable node object."""

    type = "variable"
    directive = "autodata"


class Function(Variable):
    """Function node object."""

    type = "function"
    directive = "autofunc"


class Class(Variable):
    """Class node object."""

    type = "class"
    directive = "autoclass"

    def __init__(self, *args, **kwargs):
        super(Class, self).__init__(*args, **kwargs)

        self.attributes = []
        self.methods = []

        self.read_only_properties = []
        self.read_write_properties = []

        self._obj = getattr(self.parent._obj, self.name)
        # print(self._obj.__class__.__name__.center(50, "-"))
        # for name in dir(self._obj):
        #     print(name)

        for name, _ in inspect.getmembers(
            self._obj, predicate=inspect.isfunction
        ):
            if name.startswith("_"):
                continue
            node = Method(name, parent=self, app=self._app)
            self.methods.append(node)


class Attribute(Variable):
    """Attribute node object."""

    type = "attribute"
    directive = "autoattribute"


class Method(Function):
    """Method node object."""

    type = "method"
    directive = "automethod"


class Property(Method):
    """Property node object."""

    type = "property"
    directive = "autoproperty"


class Exception_(Class):
    # pylint: disable=invalid-name
    """Exception node object."""

    type = "exception"
    direction = "autoexception"


class Module(Node):
    """Package node object."""

    type = "module"
    directive = "automodule"

    _template_file = __name__ + ".rst_t"

    def __init__(self, *args, **kwargs):
        if len(args) < 2:
            kwargs.setdefault("parent", None)
        super(Module, self).__init__(*args, **kwargs)

        self.constants = []
        self.functions = []
        self.classes = []

        self._obj = import_module(self.path, self._app)

        # Initialize jinja template.
        loader = sphinx.jinja2glue.BuiltinTemplateLoader()
        loader.init(self._app.builder, dirs=[TEMPLATE_DIR])
        environment = jinja2.sandbox.SandboxedEnvironment(loader=loader)
        self._template = environment.get_template(self._template_file)

        for name in getattr(self._obj, "__all__", dir(self._obj)):
            obj = getattr(self._obj, name)

            if name.startswith("_"):
                continue

            if isinstance(obj, types.ModuleType) or hasattr(obj, "__path__"):
                continue

            if isinstance(obj, types.FunctionType):
                node = Function(name, parent=self, app=self._app)
                self.functions.append(node)

            elif inspect.isclass(obj):
                node = Class(name, parent=self, app=self._app)
                self.classes.append(node)

            else:
                node = Variable(name, parent=self, app=self._app)
                self.constants.append(node)

    def _generate(self, out_dir):
        """Generate the rst files."""
        with open(os.path.join(out_dir, self.path + ".rst"), "w") as stream:
            stream.write(self._template.render(node=self))


class Package(Module):
    """Module node object."""

    type = "package"
    _template_file = __name__ + ".rst_t"

    def __init__(self, *args, **kwargs):
        super(Package, self).__init__(*args, **kwargs)

        self.packages = []
        self.modules = []

        for info in pkgutil.iter_modules(self._obj.__path__, self.path + "."):
            name = info.name.split(".")[-1]
            if info.ispkg:
                node = Package(name, parent=self, app=self._app)
                self.packages.append(node)
            else:
                node = Module(name, parent=self, app=self._app)
                self.modules.append(node)

    def _generate(self, out_dir):
        super(Package, self)._generate(out_dir)
        for each in self.modules + self.packages:
            each._generate(out_dir)


def builder_inited(app):
    """Called before sphinx action."""
    for module, config in getattr(app.config, CONFIG_NAME).items():

        # Create the directory.
        out_dir = os.path.join(app.srcdir, module)
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir)

        # Ensure that the files will not be pushed with git.
        with open(os.path.join(out_dir, ".gitignore"), "w") as stream:
            stream.write("*")

        # Apply default configuration.
        config = {
            "rebuild": True,
            "output": module,
        }.update(config or {})

        node = Package(module, app=app)
        node._generate(out_dir)


def setup(app):
    """Entry point of the plugin."""
    app.setup_extension("sphinx.ext.autodoc")
    app.add_config_value(CONFIG_NAME, {}, "env", dict)
    app.connect("builder-inited", builder_inited)
    return {"version": __version__}


def main():
    """Entry point of the cli."""
    return 0


if __name__ == "__main__":
    sys.exit(main())
