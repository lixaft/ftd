# pylint: disable=protected-access
"""Sphinx extension to generate API documentation."""
import copy
import importlib
import inspect
import os
import pkgutil
import shutil
import types

import jinja2.sandbox
import sphinx
import sphinx.jinja2glue

__version__ = "0.1.0"

TEMPLATE_FILE = os.path.join(
    os.path.dirname(__file__), "templates", __name__ + ".rst_t"
)

CONFIG_NAME = __name__ + "_config"
DEFAULT_CONFIG = {"runtime": {"app": None}}


def import_module(module, app):
    """Handle the import of a module by mocking them with autodoc config.

    Query the value of ``autodoc_mock_imports`` inside the ``conf.py`` module.

    Arguments:
        module (str): The name of the module to import.
        app (Sphinx): The current sphinx application.

    Returns:
        module: The python module.
    """
    with sphinx.ext.autodoc.mock(app.config.autodoc_mock_imports or []):
        return importlib.import_module(module)


class Node(object):
    """Generic node object.

    Arguments:
        name (str): The name of the node object.
        parent (Node): The parent node.
        config (dict): The configuration dictionary.
    """

    type = ""
    directive = ""

    def __repr__(self):
        return "<Node::{} '{}'>".format(self.type, self.name)

    def __init__(self, name, parent, config):
        prefix = (parent.path + ".") if parent is not None else ""

        self._config = config
        self._kwargs = {"name": name, "parent": self, "config": config}

        self.name = name
        self.path = prefix + self.name

        self.parent = parent
        self.members = []

        if parent is not None:
            parent.members.append(self)

    @property
    def is_empty(self):
        """bool: Does the node have any children?"""
        return bool(self.members)


class Variable(Node):
    """Variable node object."""

    type = "variable"
    directive = "autodata"


class Function(Variable):
    """Function node object."""

    type = "function"
    directive = "autofunction"


class Class(Variable):
    """Class node object."""

    type = "class"
    directive = "autoclass"

    def __init__(self, *args, **kwargs):
        super(Class, self).__init__(*args, **kwargs)

        self.attributes = []
        self.properties = []
        self.methods = []

        cls = getattr(self.parent._module, self.name)
        self._obj = cls

        # Register children.
        for name, obj in cls.__dict__.items():
            if name.startswith("_"):
                continue

            if isinstance(obj, property):
                self.properties.append(Property(**self._kwargs))

            elif isinstance(obj, types.MethodType):
                self.methods.append(Method(**self._kwargs))

            # obj = getattr(cls, name)

            # qualname = getattr(obj, "__qualname__", None)
            # if qualname and self.name not in qualname:
            #     continue
            # print(qualname, name, obj)

            # print(name)

        # children = [
        #     {"predicate": inspect.ismethod, "container": self.methods},
        #     {"predicate": inspect.is, "container": self.methods},
        # ]

        # for name, _ in inspect.getmembers(cls, predicate=inspect.ismethod):
        #     if name.startswith("_"):
        #         continue
        #     node = Method(name, parent=self, config=self._config)
        #     self.methods.append(node)


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

    def __init__(self, *args, **kwargs):
        # Fill the `parent` parameter.
        if len(args) < 2:
            kwargs.setdefault("parent", None)

        super(Module, self).__init__(*args, **kwargs)

        # Import the module as object.
        module = import_module(self.path, self._config["runtime"]["app"])
        self._module = module

        # Children containers.
        self.constants = []
        self.functions = []
        self.classes = []

        # Register children.
        for name in getattr(module, "__all__", dir(module)):
            if name.startswith("_"):
                continue

            # Get the python object.
            obj = getattr(module, name)

            if isinstance(obj, types.ModuleType) or hasattr(obj, "__path__"):
                continue

            if isinstance(obj, types.FunctionType):
                self.functions.append(Function(**self._kwargs))

            elif inspect.isclass(obj):
                self.classes.append(Class(**self._kwargs))

            else:
                self.constants.append(Variable(**self._kwargs))

    def _generate(self, template, output, **kwargs):
        """Generate the rst files.

        Arguments:
            template (Template): The jinja template to use to generate the doc.
            output (str): The output directory.
            **kwargs: The available keyword inside the jinja template.
        """
        with open(os.path.join(output, self.path + ".rst"), "w") as stream:
            stream.write(template.render(node=self, **kwargs))


class Package(Module):
    """Module node object."""

    type = "package"

    def __init__(self, *args, **kwargs):
        super(Package, self).__init__(*args, **kwargs)

        self.packages = []
        self.modules = []

        # Populate the children packages and modules.
        modules = pkgutil.iter_modules(self._module.__path__, self.path + ".")
        for _, name, is_package in modules:
            name = name.split(".")[-1]
            if is_package:
                node = Package(name, parent=self, config=self._config)
                self.packages.append(node)
            else:
                node = Module(name, parent=self, config=self._config)
                self.modules.append(node)

    def _generate(self, template, output, **kwargs):
        super(Package, self)._generate(template, output)
        for node in self.modules + self.packages:
            node._generate(template, output, **kwargs)


def builder_inited(app):
    """Entry point of a sphinx build.

    Arguments:
        app (Sphinx): The current sphinx application.
    """
    # Prepare the output directory.
    default = os.path.join(app.srcdir, __name__)
    if os.path.exists(default):
        shutil.rmtree(default)
    os.makedirs(default)

    # Ensure that the files will not be pushed with git.
    with open(os.path.join(default, ".gitignore"), "w") as stream:
        stream.write("*")

    for name, config in getattr(app.config, CONFIG_NAME).items():
        module = importlib.import_module(name)
        is_package = hasattr(module, "__path__")

        # Find the output directory.
        output = default
        if is_package:
            output = os.path.join(default, name)
            os.makedirs(output)

        # Initialize jinja template.
        loader = sphinx.jinja2glue.BuiltinTemplateLoader()
        loader.init(app.builder, dirs=[os.path.dirname(TEMPLATE_FILE)])
        env = jinja2.sandbox.SandboxedEnvironment(loader=loader)
        template = env.get_template(TEMPLATE_FILE)

        # Build final configuration.
        config = copy.deepcopy(DEFAULT_CONFIG)
        config.update(config or {})
        config["runtime"]["app"] = app

        node = (Package if is_package else Module)(name, config=config)
        node._generate(template, output)


def setup(app):
    """Entry point of the plugin."""
    app.setup_extension("sphinx.ext.autodoc")
    app.add_config_value(CONFIG_NAME, {}, "env", dict)
    app.connect("builder-inited", builder_inited)
    return {"version": __version__}
