"""Pythonic api for Autodesk Maya."""
import logging
import os
import sys

from maya import cmds
from maya.api import OpenMaya

# __all__ = []

LOG = logging.getLogger(__name__)


# Pytohn 2 & 3 compatibility
# pylint: disable=undefined-variable
if sys.version_info.major >= 3:
    _STRING_TYPES = (str,)
else:
    _STRING_TYPES = (basestring,)  # type: ignore
# pylint: enable=undefined-variable


def _add_metaclass(metaclass):
    """Add a metaclass compatible with python 2 and 3"""

    def _decorator(cls):
        return metaclass(cls.__name__, cls.__bases__, cls.__dict__.copy())

    return _decorator


# Global configuration
RECKLESS_MODE = bool(os.environ.get("RECKLESS_MODE", None))

# General
Fn = OpenMaya.MFn
ExistsError = type("ExistsError", (Exception,), {})


def encode(obj, default=object):
    # pylint: disable=protected-access
    """Encode an object.

    This function returns an instance of the type corresponding to the object
    passed as argument. If the object does not exist, an exception is raised,
    unless the `default` parameter is specified.

    Note:
        The default value of the ``default`` parameter is set to :obj:`object`.
        There should normally be no case where this method should return
        :obj:`object` when the node to be encoded does not exist.

        In case that is what you are looking for, it is still possible to use
        the following syntax::

            node = encode("node", default=None) or object

    If the encoding is performed on an object already encoded, returns
    the object unchanged.

    Examples:
        >>> from maya import cmds
        >>> newscene()
        >>> _ = cmds.createNode("transform", name="A")
        >>> encode("A")
        <DagNode 'A'>
        >>> encode("B")
        Traceback (most recent call last):
          ...
        RuntimeError: The object 'B' does not exists.
        >>> encode("B", default=False)
        False
        >>> _ = cmds.createNode("mutlMatrix", name="C")
        >>> encode("C")
        <DependencyNode 'C'>

    Arguments:
        obj (any): The object to encode.
        default (any): Value that is returned if the object does not exists.

    Returns:
        any: The encoded object.

    Raises:
        RuntimeError: The object does not exist and the `default` parameter
            is not specified.
        TypeError: The passed object does not contain any function set
            supported by this API.
    """
    LOG.debug("Encode: %s", repr(obj))

    # check if the object is already encoded
    if obj.__class__.__module__ == __name__:
        return obj

    # if the object passed is a character string, convert it to a maya object
    if isinstance(obj, _STRING_TYPES):
        sel = OpenMaya.MSelectionList()
        try:
            sel.add(obj)
            obj = sel.getPlug(0) if "." in obj else sel.getDependNode(0)
        except RuntimeError:
            # I need to find a way to have an optinal parameter without using
            # the default value None because the user may decide to pass None
            # in case the object does not exist. I also want to avoid using
            # **kwargs because I want to keep the ide autocompletion.
            # Any ideas? xD
            if default is not object:
                return default
            raise RuntimeError("The object '{}' does not exists.".format(obj))

    if isinstance(obj, OpenMaya.MPlug):
        return Plug(obj)

    # Ok, a little explanation on this part.
    # `getFunctionSetList` return the maya function sets inheritance list.
    # It will return a tuple of strings representing each function set that
    # the object can accept, sorted in order of inheritance. That is perfect,
    # now we just need to loop over these values to find the closest type
    # implemented here :)
    for type_ in reversed(OpenMaya.MGlobal.getFunctionSetList(obj)):
        node = MetaNode._node_types.get(getattr(Fn, type_), None)
        if node is not None:
            return node(obj)

    raise TypeError("No object function set is supported by this API.")


def decode(obj):
    """Decode an object.

    If the encoding is performed on an object that is not encoded, returns
    the object unchanged.

    Examples:
        >>> newscene()
        >>> node = create("transform", name="A")
        >>> node
        <DagNode 'A'>
        >>> decode(node)
        'A'

    Arguments:
        obj (str | Any): The object to decode.

    Returns:
        str | Any: The decoded object.
    """
    LOG.debug("Decode: %s.", repr(obj))

    if obj.__class__.__module__ != __name__:
        return obj

    if hasattr(obj, "decode"):
        return obj.decode()

    return str(obj)


def wrap(func, *args, **kwargs):
    """Wrap a third party function to allow it to work with this api.

    All arguments and keywords will be encoded before being passed to the
    function, and the result will be converted back before being returned.

    Examples:
        >>> from maya import cmds
        >>> newscene()
        >>> cmds.createNode("transform", name="A")
        'A'
        >>> wrap(cmds.createNode, "transform", name="B")
        <DagNode 'B'>

    Arguments:
        func (function): The function to wrap.
        *args: The arguments to decode and pass to the function.
        **kwargs: The keyword arguments to decode and pass to the function.

    Returns:
        any: The encoded return objects
    """

    def _convert(func_, obj):
        try:
            return func_(obj)
        except BaseException:
            return obj

    # decode each argument first
    args_ = [_convert(decode, x) for x in args]
    kwargs_ = {k: _convert(decode, v) for k, v in kwargs.items()}

    # execute the function
    returned = func(*args_, **kwargs_)
    if isinstance(returned, OpenMaya.MSelectionList):
        returned = returned.getSelectionStrings()

    # finally encode the returned object(s)
    if isinstance(returned, _STRING_TYPES):
        return _convert(encode, returned)
    if isinstance(returned, (list, tuple, set)):
        return type(returned)(_convert(encode, x) for x in returned)
    return returned


def clear():
    # pylint: disable=protected-access
    """Remove all instances stored in the memory."""
    MetaNode._instances.clear()


def newscene():
    """Create a new scene."""
    cmds.file(new=True, force=True)
    clear()


def ls(*args, **kwargs):
    # pylint: disable=invalid-name
    """Return the names of the objects in the scene.

    Wrap the `cmds.ls()`_ command.

    Tip:
        Running ``ls()`` without any arguments also has the effect of encoding
        all the nodes in the scene at once.

    Examples:
        >>> from maya import cmds
        >>> newscene()
        >>> node = cmds.createNode("transform", name="A")
        >>> cmds.select(node)
        >>> ls(selection=True)
        [<DagNode 'A'>]

    Arguments:
        *args: The arguments passed to the `cmds.ls()`_ command.
        *kwargs: The keyword arguments passed to the `cmds.ls()`_ command.

    Returns:
        list: The nodes list.

    .. _cmds.ls():
        https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/CommandsPython/ls.html
    """
    return wrap(cmds.ls, *args, **kwargs)


def selected():
    """Return the current selected nodes."""
    return wrap(OpenMaya.MGlobal.getActiveSelectionList)


# Safety
def validate(node):
    """Ensure the node are valid and will not leave Maya in an unstable state.

    Arguments:
        node: The node to validate.

    Returns:
        bool: The valid state of the passed nodes.
    """
    if node.object.isNull():
        return False
    if not node.handle.isValid():
        return False
    if not node.handle.isAlive():
        return False
    return True


# Nodes
class MetaNode(type):
    """The crossroads of node management!

    Anything involving nodes goes through here at least once :)

    Ok, big deal, but what's really going on here?

    This metaclass has two main goal:

    - Keep track of all classes that are based on it.
    - Keep track of all instances of encoded nodes so that they can be reused
      when a registered node more than once.

    We can also take advantage of some side effects of using a metaclass.
    """

    _instances = {}
    _node_types = {}

    def __new__(cls, name, bases, dict_):
        """Automatically register all new classes that use this metaclass."""
        node = super(MetaNode, cls).__new__(cls, name, bases, dict_)
        cls.register(node)
        return node

    def __call__(cls, mobject):
        """Handle the creation of instances in order to implement a singleton.

        Each encoded node will be stored in a dictionary and when a second
        encoding attempt is made on this node, the previous instance will be
        reused instead of creating a new one.

        Examples:
            >>> from maya import cmds
            >>> newscene()
            >>> _ = cmds.createNode("transform", name="A")
            >>> _ = cmds.createNode("transform", name="B")
            >>> a = encode("A")
            >>> b = encode("B")
            >>> a is b
            False
            >>> c = encode("A")
            >>> a is c
            True

        Note:
            Make a comparison using ``is`` is equivalent to comparing the
            :func:`id` of the two operands. So ``a is b`` is equivalent to
            ``id(a) == id(b)``.

        .. admonition:: How it works?
            :class: maya

            In order to be able to retrive a reused node, we need a unique
            identifier for each node that will be used during their comparison.
            There are two possibilities, uuid and hash code.

            **UUID**

            Every node has a attribute called ``uuid`` stored on it which,
            as the name suggest, is unique. That's perfect! Well not so much.
            Take a same scene that is referenced twice in another scene.
            Each node from the referencde scene is present twice in the scene,
            with the same uuid. And this is a problem because we have no way to
            differentiate these two nodes in an efficient way.

            **Hash code**

            For each MObject, maya provides an hash code.
            The `official documentation`_ says:

                [...] several internal Maya objects may return the same code.
                However different MObjectHandles whose MObjects refer to the
                same internal Maya object will return the same hash code.
                [...]

            Which is exactly what we want.

        Arguments:
            mobject (MObject): The maya object used to initialize the instance.

        Returns:
            any: The new instance or the reused one if it already exists.

        .. _official documentation:
            https://help.autodesk.com/cloudhelp/2020/ENU/Maya-SDK-MERGED/cpp_ref/class_m_object_handle.html#a23a0c64be863c23d2cf8214243d59bb1
        """
        handle = OpenMaya.MObjectHandle(mobject)
        hash_ = handle.hashCode()

        # if the instance is already created, return it as-is
        if hash_ in cls._instances:
            return cls._instances[hash_]

        # otherwise, initialize the instance and register it
        self = super(MetaNode, cls).__call__(mobject)
        self._handle = handle
        cls._instances[hash_] = self
        return self

    @classmethod
    def register(cls, node):
        # pylint: disable=protected-access
        """Register a new type of node.

        This allows the encoder to know all the possibilities it has to encode
        a node to find the closest match to its original type.
        """
        cls._node_types[node._fn_id] = node
        return node


@_add_metaclass(MetaNode)
class DependencyNode(object):
    """A Dependency Graph (DG) node."""

    _fn_id = Fn.kDependencyNode
    _fn_set = OpenMaya.MFnDependencyNode

    def __repr__(self):
        """Return ``repr(self)``."""
        return "<{} '{}'>".format(self.__class__.__name__, self)

    # Conversion methods ---
    def __str__(self):
        """Return ``str(self)``."""
        return self.fn.name()

    def __bool__(self):
        """Return ``bool(self)``."""
        return True

    __nonzero__ = __bool__

    # Arithmetic operators ---
    def __add__(self, other):
        """Return ``self + other``."""
        return str(self) + str(other)

    # Reflected arithmetic operators ---
    def __radd__(self, other):
        """Return ``other + self``."""
        return str(other) + str(self)

    # Comparison operators ---
    def __eq__(self, other):
        """Return ``self == other``."""
        return str(self) == str(other)

    def __ne__(self, other):
        """Return ``self != other``."""
        return str(self) != str(other)

    # Container type ---
    def __getitem__(self, key):
        """Return ``self[key]``."""
        return self.findplug(key)

    def __setitem__(self, key, value):
        """Set ``self[key]`` to ``value``."""
        print(key, value)

    # ---
    def __init__(self, mobject):
        self._object = mobject
        self._fn = self._fn_set(mobject)
        self._handle = None

    # Read properties ---
    @property
    def object(self):
        """MObject: The maya object attached to self."""
        return self._object

    @property
    def handle(self):
        """MObjectHandle: The maya object handle attached to self."""
        return self._handle

    @property
    def fn(self):
        # pylint: disable=invalid-name
        """MFnDependencyNode: The maya function set attached to self."""
        return self._fn

    @property
    def type(self):
        """str: The type name of the node."""
        return self.fn.typeName

    @property
    def typeid(self):
        """int: A bit number that is used to identify the type of the node in
        binary file format.
        """
        return self.fn.typeId.id()

    @property
    def uuid(self):
        """str: The Universally Unique Identifier (UUID) of the node."""
        return self.fn.uuid().asString()

    @property
    def hash(self):
        """int: Hash code for the internal maya object.

        The hash code is not unique, several MObjects can have the same hash
        code. However, if different MObectHandle refer to the same maya
        internal object, they will return the same hash code
        """
        return self._handle.hashCode()

    @property
    def isdefault(self):
        """bool: True if the node is created automatically by Maya."""
        return self.fn.isDefaultNode()

    @property
    def isreferenced(self):
        """bool: True if the node come from a referenced file."""
        return self.fn.isFromReferencedFile()

    # Read write properties ---
    @property
    def name(self):
        """str: The name of the node."""
        return self.fn.name()

    @name.setter
    def name(self, value):
        self.fn.setName(value)

    @property
    def lock(self):
        """bool: The lock state of the node.

        A locked node means that it cannot be deleted, repaired or renamed.
        It is also not possible to create, edit or delete their attributes.
        """
        return self.fn.isLocked

    @lock.setter
    def lock(self, value):
        self.fn.isLocked = value

    # Public methods ---
    def findplug(self, attribute):
        # pylint: disable=protected-access
        """Attempt to find a plug for the given attribute.

        Arguments:
            attribute (str): The name of the attribute to search for.

        Returns:
            Plug: The instance of the plug.
        """
        try:
            plug = Plug(self.fn.findPlug(attribute, False))
            plug._node = self
            return plug
        except RuntimeError:
            message = "The plug '{}.{}' does not exists."
            raise ExistsError(message.format(self, attribute))

    def related(self, up=True, down=True, filters=None):
        # pylint: disable=invalid-name, unused-argument
        """Iterate through the graph."""
        mit = OpenMaya.MItDependencyGraph
        directions = {mit.kUpstream: up, mit.kDownstream: down}
        for direction in (k for k, v in directions.items() if v):
            iterator = mit(
                self.object,
                direction=direction,
                traversal=mit.kDepthFirst,
                level=mit.kNodeLevel,
            )
            # skip self
            iterator.next()
            while not iterator.isDone():
                obj = iterator.currentNode()
                yield encode(obj)
                iterator.next()

    def history(self, filters=None):
        """The upstream version of :meth:`related`."""
        return self.related(up=True, down=False, filters=filters)

    def future(self, filters=None):
        """The downstream version of :meth:`related`."""
        return self.related(up=False, down=True, filters=filters)


class DagNode(DependencyNode):
    """A Dependency Graph (DG) node."""

    _fn_id = Fn.kDagNode
    _fn_set = OpenMaya.MFnDagNode


class Set(DependencyNode):
    """An object set node."""

    _fn_id = Fn.kSet
    _fn_set = OpenMaya.MFnSet


def create(type_, name=None, **kwargs):
    """Create a new node.

    By default, this function simply wraps the cmds.createNode()`_ command.

    Examples:
        >>> newscene()
        >>> a = create("transform", name="A")
        >>> a
        <DagNode 'A'>
        >>> create("joint", name="B", parent=a)
        <DagNode 'B'>

    Arguments:
        type_ (str): The type of the node to create.
        name (str): The name of the node to create. If not specified,
            use the `type_` parameter instead.
        **kwargs: The additional keyword arguments to pass to the
            `cmds.createNode()`_ command.

    Returns:
        DependencyNode: A node instace based on the type of the node.

    .. _cmds.createNode():
        https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/CommandsPython/createNode.ht
    """
    return wrap(cmds.createNode, type_, name=name or type_, **kwargs)


def exists(obj):
    """Check if the specified object exists or not.

    Examples:
        >>> newscene()
        >>> exists("A")
        False
        >>> _ = create("transform", name="A")
        >>> exists("A")
        True

    Arguments:
        obj (str): The name of the object to check.

    Returns:
        bool: True if the object exists, otherwise False.
    """
    try:
        sel = OpenMaya.MSelectionList()
        sel.add(str(obj))
        return True
    except RuntimeError:
        return False


def delete(*args, **kwargs):
    """Delete the specified nodes.

    Wrap the `cmds.delete()`_ command.

    Examples:
        >>> newscene()
        >>> node = create("transform")
        >>> exists(node)
        True
        >>> delete(node)
        >>> exists(node)
        False

    Arguments:
        *args: The arguments passed to the `cmds.delete()`_ command.
        *kwargs: The keyword arguments passed to the `cmds.delete()`_ command.

    Returns:
        list: The nodes list.

    .. _cmds.delete():
        https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/CommandsPython/delete.html
    """
    return wrap(cmds.delete, *args, **kwargs)


# plug
class Plug(object):
    """Plug object."""

    def __repr__(self):
        return "<Plug '{}'>".format(self)

    def __str__(self):
        return self.plug.name()

    def __init__(self, mplug):
        self._plug = mplug
        self._node = None

    # Read properties ---
    @property
    def plug(self):
        """MPlug: The maya plug attached to self."""
        if self._plug is None:
            self._plug = encode(self.plug.node())
        return self._plug

    @property
    def node(self):
        """DependencyNode: The node associated to self."""
        return self._node


# Privates


# MIT License

# Copyright (c) 2021 Fabien Taxil

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
