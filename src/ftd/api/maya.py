# pylint: disable=invalid-name, redefined-builtin, protected-access
"""Object-oriented API for Autodesk Maya."""
from __future__ import absolute_import, division

import abc
import logging
import math
import sys
import types

from maya import cmds
from maya.api import OpenMaya

__version__ = "0.1.0"
__all__ = [
    # Common
    "clear",
    "newscene",
    "exists",
    # Enum
    "Space",
    # Encoding & Decoding
    "encode",
    "decode",
    # Nodes
    "DependencyNode",
    "DagNode",
    "create",
    "delete",
    # Plug & Attributes
    "Plug",
    # Data types
    "Vector",
]

LOG = logging.getLogger(__name__)

# Pytohn 2 & 3 compatibility.
# pylint: disable=undefined-variable
_STRING_TYPES = str if sys.version_info[0] >= 3 else basestring  # type: ignore
# pylint: enable=undefined-variable


def _add_metaclass(metaclass):
    """Add a metaclass compatible with python 2 and 3"""

    def _decorator(cls):
        return metaclass(cls.__name__, cls.__bases__, cls.__dict__.copy())

    return _decorator


# Errors
DgError = type("DgError", (Exception,), {})
DagError = type("DagError", (Exception,), {})
ExistsError = type("ExistsError", (Exception,), {})
PlugError = type("PlugError", (Exception,), {})
GraphError = type("GraphError", (Exception,), {})


# Common
def newscene():
    """Create a new scene."""
    cmds.file(new=True, force=True)
    clear()


def clear():
    """Remove all instances stored in the memory."""
    _MetaNode._instances.clear()


# Enum
class Space(object):
    """Space transformation identifiers."""

    TRANSFORM = OpenMaya.MSpace.kTransform
    PRE_TRANSFORM = OpenMaya.MSpace.kPreTransform
    POST_TRANSFORM = OpenMaya.MSpace.kPostTransform
    WORLD = OpenMaya.MSpace.kWorld
    OBJECT = OpenMaya.MSpace.kObject


# Encoding & Decoding
def encode(obj, default=object):
    """Encode an object.

    Create an instance of the type corresponding to the object passed as a
    parameter. If the object does not exist in Maya, raises an exception of
    type `ValueError` unless a value is specified in the default parameter and
    then returns that value.

    Note:
        The default value of ``default`` parameter is initialized to
        :obj:`object`. Indeed, using the "normal" method by initializing it the
        None, will make it impossible for the user to use the value None to
        specify the default return value.

        I didn't any case or the user would return :obj:`object` but in case or
        it is what you want, you can still use a "derived" synthax::

            >>> encode("unknown", default=None) or object
            <class 'object'>

    If the encoding is performed on an object already encoded, returns
    the object unchanged.

    Examples:
        >>> from maya import cmds
        >>> newscene()
        >>> _ = cmds.createNode("transform", name="A")
        >>> encode("A")
        <DagNode 'A' type::transform>
        >>> encode("B")
        Traceback (most recent call last):
          ...
        ValueError
        >>> encode("B", default=False)
        False
        >>> _ = cmds.createNode("multMatrix", name="C")
        >>> encode("C")
        <DependencyNode 'C' type::multMatrix>

    Arguments:
        obj (any): The object to encode.
        default (any): Value that is returned if the object does not exists.

    Returns:
        any: The encoded object.

    Raises:
        TypeError: The type of the object is not supported.
        ValueError: The object does not exist and the `default` parameter
            is not specified.
    """
    LOG.debug("Encoding: %s", repr(obj))

    # Check if the object is not already encoded.
    if obj.__class__.__module__ == __name__:
        return obj

    if isinstance(obj, _STRING_TYPES):
        sel = OpenMaya.MSelectionList()
        try:
            sel.add(obj)
            if "." in obj:
                obj = sel.getPlug(0)
            else:
                obj = sel.getDependNode(0)
        except RuntimeError:
            if default is not object:
                return default
            raise ValueError("The object '{}' does not exists.".format(obj))

    if isinstance(obj, OpenMaya.MPlug):
        return Plug(obj)

    if not isinstance(obj, OpenMaya.MObject):
        msg = "The object type {} is not supported."
        raise TypeError(msg.format(type(obj)))

    # Find the most appropriate class in which the object can be encoded.
    for each in reversed(OpenMaya.MGlobal.getFunctionSetList(obj)):
        cls = _MetaNode._types.get(getattr(OpenMaya.MFn, each))
        if cls is not None:
            return cls(obj)

    raise ValueError("Failed to encode the object '{}'".format(obj))


def decode(obj, **kwargs):
    """Decode an object."""
    LOG.debug("Decode: %s", repr(obj))

    if obj.__class__.__module__ != __name__:
        return obj

    if hasattr(obj, "decode"):
        return obj.decode(**kwargs)

    return str(obj)


def ls(*args, **kwargs):
    """Todo."""
    return _wrap(cmds.ls, *args, **kwargs)


def selected():
    """Return the current selected nodes."""
    selection = OpenMaya.MGlobal.getActiveSelectionList().getSelectionStrings()
    return map(encode, selection)


# Nodes
class _MetaNode(type):
    """Manage all the registered nodes.

    Anything involving nodes goes through here at least once :)

    This meta class has to main goal:
    - Keep track of all classes that are based on it.
    - Keep track of all instances of encoded nodes so that they can be reused
      when a registered node more than once.
    """

    _types = {}
    _instances = {}

    def __new__(mcs, name, bases, dict_):
        """Register all new classes that derive from this metaclass."""
        cls = super(_MetaNode, mcs).__new__(mcs, name, bases, dict_)
        mcs._types[cls._identifier] = cls
        return cls

    def __call__(cls, mobject, *args, **kwargs):
        """Handle the creation of instances in order to implement a singleton.

        Each node will be tracked and stored in a python dictionary in order to
        reuse the same instance for all encoding attempts on the same node.

        Note:
            Make a comparison using ``is`` is equivalent to comparing the
            :func:`id` of the two operands. So ``a is b`` is equivalent to
            ``id(a) == id(b)``.

        How it works?
            To be able to retrieve if a node has already been encoded or not,
            we need to find a way to effectively compare nodes.

            Using the node name is a very bad idea, as two nodes can have the
            same name in the same scene, and the node name is not constant
            within a session

            Maya provides two different systems that can be used to efficiently
            compare nodes, UUIDs or hash codes.

            **Universally unique identifier (UUID)**

            Every node has a attribute called ``uuid`` stored on it which,
            as the name suggest, is unique. That's perfect! Well not so much.
            Take a same scene that is referenced twice in another scene.
            Each node from the referencde scene is present twice in the scene,
            with the same uuid. And this is a problem because we have no way to
            differentiate these two nodes in an efficient way.

            **Hash code**

            For each MObject, maya provides an hash code. On the subject, the
            `official documentation`_ says:

                [...] several internal Maya objects may return the same code.
                However different MObjectHandles whose MObjects refer to the
                same internal Maya object will return the same hash code.
                [...]

            Which is exactly what we want.

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

        Arguments:
            mobject (MObject): The maya object used to initialize the instance.

        Returns:
            any: The encoded instance of the node.

        .. _official documentation:
            https://help.autodesk.com/cloudhelp/2020/ENU/Maya-SDK-MERGED/cpp_ref/class_m_object_handle.html#a23a0c64be863c23d2cf8214243d59bb1
        """
        handle = OpenMaya.MObjectHandle(mobject)
        hash_code = handle.hashCode()

        self = cls._instances.get(hash_code)
        if not self:
            self = super(_MetaNode, cls).__call__(mobject, *args, **kwargs)
            self._handle = handle
            cls._instances[hash_code] = self
        return self


@_add_metaclass(_MetaNode)
class DependencyNode(object):
    """A Dependency Graph (DG) node."""

    _class = OpenMaya.MFnDependencyNode
    _identifier = OpenMaya.MFn.kDependencyNode

    def __repr__(self):
        return "<{} '{}' type::{}>".format(
            self.__class__.__name__,
            self.fn.name(),
            self.fn.typeName,
        )

    # Type conversion ---
    def __str__(self):
        return self.fn.name()

    def __bool__(self):
        return True

    __nonzero__ = __bool__

    # Arithmetic operators ---
    def __add__(self, other):
        """Allow the legacy way to acess plugs.

        Examples:
            >>> newscene()
            >>> a = create("transform", name="A")
            >>> a + ".translateX"
            'A.translateX'
        """
        return str(self) + str(other)

    # Reflected arithmetic operators ---
    def __radd__(self, other):
        return str(other) + str(self)

    # Comparison operators ---
    def __eq__(self, other):
        if isinstance(other, DependencyNode):
            return self.object == other.object
        return str(self) == str(other)

    def __ne__(self, other):
        if isinstance(other, DependencyNode):
            return self.object != other.object
        return str(self) != str(other)

    # Emmulate container type ---
    def __getitem__(self, key):
        return self.findplug(key)

    def __setitem__(self, key, value):
        self.findplug(key).value = value

    # Constructor ---
    def __init__(self, mobject):
        self._object = mobject
        self._fn = self._class(mobject)
        self._handle = OpenMaya.MObjectHandle(mobject)

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
    def inherited(self):
        """list: The type inheritance of the node."""
        return cmds.nodeType(self.name, inherited=True)

    @property
    def derived(self):
        """list: The types that inherits of the node."""
        return cmds.nodeType(self.name, derived=True)

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
        return self.handle.hashCode()

    @property
    def isdefault(self):
        """bool: True if the node is created automatically by Maya."""
        return self.fn.isDefaultNode

    @property
    def isreferenced(self):
        """bool: True if the node come from a referenced file."""
        return self.fn.isFromReferencedFile

    # Read write properties ---
    @property
    def name(self):
        """str: The name of the node."""
        return self.fn.name()

    @name.setter
    def name(self, value):
        cmds.rename(self.name, value)

    @property
    def lock(self):
        """bool: The lock state of the node.

        A locked node means that it cannot be deleted, repaired or renamed.
        It is also not possible to create, edit or delete their attributes.
        """
        return self.fn.isLocked

    @lock.setter
    def lock(self, value):
        cmds.lockNode(self.name, lock=value)

    # Public methods ---
    def duplicate(self, name=None):
        """Duplicate the node.

        Examples:
            >>> newscene()
            >>> a = create("transform", name="A")
            >>> b = a.duplicate("B")
            >>> b
            <DagNode 'B' type::transform>
            >>> a != b
            True

        Arguments:
            name (str): The name to give to the duplicate node.

        Returns:
            DependencyNode: The instance of the duplicate node.
        """
        return encode(cmds.duplicate(self.name, name=name)[0])

    def delete(self):
        """Delete the node.

        Warning:
            Even if the node is deleted, its instance still exists in memory.
            Attempting to access a deleted node may cause a crash.

        Examples:
            >>> newscene()
            >>> node = create("transform")
            >>> exists(node)
            True
            >>> node.delete()
            >>> exists(node)
            False
        """
        cmds.delete(self.name)

    def findplug(self, attribute):
        """Find a plug from an attribute name.

        Examples:
            >>> newscene()
            >>> node = create("transform", name="A")
            >>> node.findplug("message")
            <Plug 'A.message' type::message>
            >>> node.findplug("unknown")
            Traceback (most recent call last):
              ...
            ValueError

        Arguments:
            attribute (str): The name of the attribute to search for.

        Returns:
            Plug: The instance of the plug.

        Raises:
            ValueError: The attribute does not exists on the node.
        """
        LOG.debug("Acess '%s.%s'", self.name, attribute)
        try:
            return Plug(self.fn.findPlug(attribute, False))
        except RuntimeError:
            message = "The plug '{}.{}' does not exists."
            raise ValueError(message.format(self, attribute))

    def history(self, filter=None):
        """Search in the node history."""
        return self._related(OpenMaya.MItDependencyGraph.kUpstream, filter)

    def future(self, filter=None):
        """Search in the future of the node."""
        return self._related(OpenMaya.MItDependencyGraph.kDownstream, filter)

    def istype(self, filter, strict=False):
        """Check the type of the node.

        Arguments:
            filter (str, tuple): The node(s) that should match with self.
            strict (bool): If `True`, does not check for inherited types and
                return `True` only if self has the exact same type as the on of
                the specified filter.

        Returns:
            bool: `True` if self match the filter otherwise `False`.
        """
        if strict:
            return self.type in filter
        if isinstance(filter, _STRING_TYPES):
            filter = [filter]
        return any(x in self.inherited for x in filter)

    # Private methods ---
    def _related(self, direction, filter=None):
        """Retrive node through the graph."""
        iterator = OpenMaya.MItDependencyGraph(
            self.object,
            direction,
            traversal=OpenMaya.MItDependencyGraph.kDepthFirst,
            level=OpenMaya.MItDependencyGraph.kNodeLevel,
        )

        # Skip self.
        iterator.next()

        while not iterator.isDone():
            node = encode(iterator.currentNode())
            # print(node.type, filter)
            if filter is None or node.type in filter:
                yield node
            iterator.next()


class DagNode(DependencyNode):
    """A Directed Acyclic Graph (DAG) node."""

    _class = OpenMaya.MFnDagNode
    _identifier = OpenMaya.MFn.kDagNode

    def __len__(self):
        return self.childcount

    def __iter__(self):
        return self.children()

    def __init__(self, mobject):
        super(DagNode, self).__init__(mobject)
        self._dagpath = OpenMaya.MDagPath.getAPathTo(self.object)

    # Read properties ---
    @property
    def dagpath(self):
        """MDagPath: The dag path instance associated to the node."""
        return self._dagpath

    @property
    def path(self):
        """str: The path of the attached object from the root of the DAG."""
        return self.fn.fullPathName()

    @property
    def childcount(self):
        """int: The number of chidren of the node"""
        return self.fn.childCount()

    # Public methods ---
    def root(self):
        """The root node of the first path leading to this node.

        Examples:
            >>> newscene()
            >>> a = create("transform", name="A")
            >>> b = create("transform", name="B")
            >>> c = create("transform", name="C")
            >>> a.addchild(b)
            >>> b.addchild(c)
            >>> c.root()
            <DagNode 'A' type::transform>

        Returns:
            DagNode: The root node.
        """
        parents = list(self.parents())
        if len(parents) > 0:
            return parents[-1]
        return None

    def parents(self, filter=None, strict=False):
        """Find the parents nodes.

        Examples:
            >>> newscene()
            >>> a = create("transform", name="A")
            >>> b = create("transform", name="B")
            >>> c = create("transform", name="C")
            >>> a.addchild(b)
            >>> b.addchild(c)
            >>> list(c.parents())
            [<DagNode 'B' type::transform>, <DagNode 'A' type::transform>]

        Arguments:
            filter (str, tuple): Filter the returned node types.
            strict (bool): If `True`, does not check for inherited types and
                return `True` only if self has the exact same type as the on of
                the specified filter.

        Yield:
            DagNode: The next parent node.
        """
        # The `parentCount` and `parent` (with an index other than 0)
        # methods seem does not to work...
        mobject = self.fn.parent(0)
        while mobject.apiType() != OpenMaya.MFn.kWorld:
            parent = encode(mobject)
            if _match_filter(parent, filter, strict):
                yield parent
            mobject = parent.fn.parent(0)

    def parent(self, index=None):
        """Find a parent node.

        Examples:
            >>> newscene()
            >>> a = create("transform", name="A")
            >>> b = create("transform", name="B")
            >>> a.addchild(b)
            >>> b.parent()
            <DagNode 'A' type::transform>

        Arguments:
            index (int): The index of the parent to find.

        Returns:
            DagNode: The parent node.

        Raises:
            DagError: The parent at the speicified index is inaccessible.
        """
        try:
            parents = list(self.parents())
            return parents[index or 0]
        except IndexError:
            if index is None:
                return None
            msg = "The parent node at the index '{}' is inaccessible."
            raise DagError(msg.format(index))

    def siblings(self, filter=None, strict=False):
        """Find the siblings nodes

        Examples:
            >>> newscene()
            >>> a = create("transform", name="A")
            >>> b = create("transform", name="B")
            >>> c = create("transform", name="C")
            >>> d = create("transform", name="D")
            >>> a.addchildren(b, c, d)
            >>> list(b.siblings())
            [<DagNode 'C' type::transform>, <DagNode 'D' type::transform>]

        Arguments:
            filter (str, tuple): Filter the returned node types.
            strict (bool): If `True`, does not check for inherited types and
                return `True` only if self has the exact same type as the on of
                the specified filter.

        Yield:
            DagNode: The next sibling node.
        """
        parent = self.parent()
        if parent is None:
            nodes = ls(assemblies=True)
        else:
            nodes = parent.children()

        for node in nodes:
            if node != self and _match_filter(node, filter, strict):
                yield node

    def sibling(self, index=None):
        """Find a sibling node.

        Examples:
            >>> newscene()
            >>> a = create("transform", name="A")
            >>> b = create("transform", name="B")
            >>> c = create("transform", name="C")
            >>> a.addchildren(b, c)
            >>> b.sibling()
            <DagNode 'C' type::transform>

        Arguments:
            index (int): The index of the sibling to find.

        Returns:
            DagNode: The sibling node.

        Raises:
            DagError: The sibling at the speicified index is inaccessible.
        """
        try:
            siblings = list(self.siblings())
            return siblings[index or 0]
        except IndexError:
            if index is None:
                return None
            msg = "The sibling node at the index '{}' is inaccessible."
            raise DagError(msg.format(index))

    def shapes(self, filter=None, strict=False):
        """Find the shape nodes.

        Arguments:
            filter (str, tuple): Filter the returned node types.
            strict (bool): If `True`, does not check for inherited types and
                return `True` only if self has the exact same type as the on of
                the specified filter.

        Yield:
            Shape: The next shape node.
        """
        for index in range(self.fn.childCount()):
            obj = self.fn.child(index)
            if obj.hasFn(OpenMaya.MFn.kShape):
                child = encode(obj)
                if _match_filter(child, filter, strict):
                    yield child

    def shape(self, index=None):
        """Find a shape node.

        Arguments:
            index (int): The index of the shape to find.

        Returns:
            Shape: The shape node.

        Raises:
            DagError: The shape at the speicified index is inaccessible.
        """
        try:
            shapes = list(self.shapes())
            return shapes[index or 0]
        except IndexError:
            if index is None:
                return None
            msg = "The shape node at the index '{}' is inaccessible."
            raise DagError(msg.format(index))

    def children(self, recurse=False, shape=False, filter=None, strict=False):
        """Find the child nodes.

        Arguments:
            recurse (bool): Include all descendants in the yielded nodes
                instead of the just the children.
            shape (bool): Include the shapes in the yielded nodes.
            filter (str, tuple): Filter the returned node types.
            strict (bool): If `True`, does not check for inherited types and
                return `True` only if self has the exact same type as the on of
                the specified filter.

        Yield:
            DagNode: The next child node.
        """
        for index in range(self.fn.childCount()):
            child = encode(self.fn.child(index))

            if _match_filter(child, filter, strict):
                if not (child.object.hasFn(OpenMaya.MFn.kShape) and not shape):
                    yield child

            if recurse:
                for each in child.children(recurse=True, filter=filter):
                    yield each

    def child(self, index=None):
        """Find a child node.

        Arguments:
            index (int): The index of the child to find.

        Returns:
            DagNode: The child node.

        Raises:
            DagError: The child at the speicified index is inaccessible.
        """
        try:
            children = list(self.children())
            return children[index or 0]
        except IndexError:
            if index is None:
                return None
            msg = "The sibling node at the index '{}' is inaccessible."
            raise DagError(msg.format(index))

    def addchild(self, node, index=None):
        """Add a child to the node.

        Arguments:
            node (DagNode): The node to add.
            index (int): The index at which the node will be inserted into the
                children.
        """
        node._set_parent(self)
        if index is not None:
            offset = -self.childcount + index + 1
            cmds.reorder(node.name, relative=offset)

    def addchildren(self, *args):
        """Recursively add multiple children to the node.

        Arguments:
            *args: The nodes to add as child.
        """
        for arg in args:
            if isinstance(arg, (list, tuple, set, types.GeneratorType)):
                self.addchildren(*arg)
            else:
                self.addchild(arg)

    def hide(self):
        """Set the visibility plug to False."""
        self["visibility"] = False

    def show(self):
        """Set the visibility plug to True."""
        self["visibility"] = True

    # Private methods ----
    def _set_parent(self, parent):
        """Set the parent of self in the outliner."""
        if self.parent() == parent:
            LOG.debug("%s is already a child of %s.", self, parent)
        else:
            cmds.parent(self.name, str(parent))


class Shape(DagNode):
    """A shape node."""

    _identifier = OpenMaya.MFn.kShape

    def _set_parent(self, parent):
        cmds.parent(self.name, parent.name, shape=True, relative=True)


def exists(obj):
    """Check if an object exists in the scene."""
    return cmds.objExists(str(obj))


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
        **kwargs: The keyword arguments passed to the `cmds.delete()`_ command.

    .. _cmds.delete():
        https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/CommandsPython/delete.html
    """
    return _wrap(cmds.delete, *args, **kwargs)


# Creator
@_add_metaclass(abc.ABCMeta)
class Creator(object):
    """Allow to customize the creation of nodes."""

    identifier = None
    _registered = {}

    def __repr__(self):
        return "<Creator '{}'>".format(self.identifier)

    @classmethod
    def register(cls, creator):
        """Register a new creator.

        Arguments:
            creator (class): The creator to register.

        Returns:
            class: The registered class.

        Raises:
            TypeError: Invalid creator type.
        """
        if not issubclass(creator, Creator):
            raise TypeError("Invalid creator. Must be derivied of Creator.")
        cls._registered[creator.identifier] = creator
        return creator

    @abc.abstractmethod
    def create(self, name=None):
        """Create a new node.

        Arguments:
            name (str): The name to give to the new node.

        Returns:
            DependencyNode: The created node.
        """


@Creator.register
class LocatorCreator(Creator):
    """Create a new locator."""

    identifier = "locator"

    def create(self, name=None):
        return encode(cmds.spaceLocator(name=name or self.identifier)[0])


def create(type, name=None, **kwargs):
    """Create a new node.

    Arguments:
        type (str): The type of the node to create.
        name (str): The name of the node to create. If not specified,
            use the ``type`` parameter instead.
        **kwargs: The additional keyword arguments to pass to the
            :class:`Creator` or to the `cmds.createNode()`_ command.

    Returns:
        DependencyNode: A node instace based on the type of the node.

    .. _cmds.createNode():
        https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/CommandsPython/createNode.html
    """
    if type in Creator._registered:
        type = Creator._registered[type](**kwargs)

    if isinstance(type, Creator):
        return type.create(name)

    return _wrap(cmds.createNode, type, name=name or type, **kwargs)


# Plug & Attributes
class Plug(object):
    """A plug object."""

    def __repr__(self):
        return """<{} '{}' type::{}>""".format(
            self.__class__.__name__,
            self.name,
            self.type,
        )

    def __str__(self):
        return self.name

    def __init__(self, mplug):
        self._plug = mplug

    # Read properties ---
    @property
    def plug(self):
        """MPlug: The mplug instance of the plug."""
        return self._plug

    @property
    def node(self):
        """DependencyNode: Get the associated node."""
        return encode(self.plug.node())

    @property
    def name(self):
        """str: The plug name."""
        return self.plug.name()

    @property
    def attribute(self):
        """str: THe attribute name of the plug."""
        return str(self).rsplit(".", 1)[-1]

    @property
    def type(self):
        """str: The plug type."""
        return cmds.getAttr(self.name, type=True)

    @property
    def issettable(self):
        """bool: The plug is settable."""
        return self.plug.isFreeToChange() == OpenMaya.MPlug.kFreeToChange

    @property
    def isdefault(self):
        """bool: The plug is default value."""
        return self.plug.isDefaultValue()

    @property
    def isarray(self):
        """bool: True if plug is an array of plugs."""
        return self.plug.isArray

    @property
    def iscompound(self):
        """str:  True if plug is compound parent with children."""
        return self.plug.isCompound

    @property
    def childcount(self):
        """int: The number of chidren of the node.

        Raises:
            TypeError: self has no child.
        """
        if self.isarray:
            return self.plug.evaluateNumElements()
        if self.iscompound:
            return self.plug.numChildren()
        return 0

    # Read write properties ---
    @property
    def value(self):
        """any: The value of the plug."""
        return self._read()

    @value.setter
    def value(self, value):
        return self._write(value)

    @property
    def default(self):
        """any: The plug is default value."""
        value = cmds.attributeQuery(
            self.attribute,
            node=self.node.name,
            listDefault=True,
        )
        if isinstance(value, (list, tuple)) and len(value) == 1:
            value = value[0]
        return value

    @default.setter
    def default(self, value):
        cmds.addAttr(self.name, edit=True, defaultValue=value)

    # Private methods ---
    def _read(self):
        """Read the value from the plug."""
        return cmds.getAttr(self.name)

    def _write(self, value):
        """Set the value of the plug."""
        cmds.setAttr(self.name, value)


# Data types
class Point(object):
    """3D point."""

    def __repr__(self):
        return "<Vector {}>".format(self)

    # Type conversion ---
    def __str__(self):
        return str(tuple(self))

    def __init__(self, x=0, y=0, z=0, w=1):
        self._point = OpenMaya.MPoint(x, y, z, w)

    @classmethod
    def from_mpoint(cls, mpoint):
        """Create a point from a maya point."""
        return cls(mpoint.x, mpoint.y, mpoint.z, mpoint.w)


class Vector(object):
    """Three dimensional vector.

    Arguments:
        x (float): The x component of the vector.
        y (float): The y component of the vector.
        z (float): The z component of the vector.
    """

    def __repr__(self):
        return "<Vector {}>".format(self)

    # Unary operators ---
    def __pos__(self):
        """Positive version of the vector (doesn't do anything)."""
        return Vector(+self.x, +self.y, +self.z)

    def __neg__(self):
        """Negate all components of the vector."""
        return Vector(-self.x, -self.y, -self.z)

    def __abs__(self):
        """Convert all negative components to positive."""
        return Vector(abs(self.x), abs(self.y), abs(self.z))

    def __round__(self, ndigits=0):
        """Round all components of the vector."""
        return Vector(
            round(self.x, ndigits),
            round(self.y, ndigits),
            round(self.z, ndigits),
        )

    def __ceil__(self):
        """Converts all floating numbers to the next integer."""
        return Vector(
            math.ceil(self.x),
            math.ceil(self.y),
            math.ceil(self.z),
        )

    def __floor__(self):
        """Converts all floating numbers to the previous integer."""
        return Vector(
            math.floor(self.x),
            math.floor(self.y),
            math.floor(self.z),
        )

    def __trunc__(self):
        """Converts all floating numbers to the closest integer."""
        return Vector(
            math.trunc(self.x),
            math.trunc(self.y),
            math.trunc(self.z),
        )

    # Type conversion ---
    def __str__(self):
        return str(tuple(self))

    # Arithmetic operators ---
    def __add__(self, vector):
        return self.from_mvector(self.vector + vector.vector)

    def __sub__(self, vector):
        return self.from_mvector(self.vector - vector.vector)

    def __mul__(self, scalar):
        """Compute the dot product."""
        return self.from_mvector(self.vector * scalar)

    def __truediv__(self, scalar):
        return self.from_mvector(self.vector / scalar)

    def __xor__(self, vector):
        """Compute the cross product."""
        return self.from_mvector(self.vector ^ vector.vector)

    # Comparison operators ---
    def __eq__(self, vector):
        """Return True if all components are identical."""
        if isinstance(vector, (list, tuple)):
            return type(vector)(self) == vector
        return self.vector == vector.vector

    def __ne__(self, vector):
        """Return True if at least one of the components is not identical."""
        if isinstance(vector, (list, tuple)):
            return type(vector)(self) != vector
        return self.vector != vector.vector

    # Emmulate container type ---
    def __len__(self):
        return 3

    def __getitem__(self, key):
        """Allow access to components via the container synthax.

        Examples:
            >>> v = Vector(1, 2, 3)
            >>> v[0] == v["x"] == 1
            True
            >>> v[1] == v["y"] == 2
            True
            >>> v[2] == v["z"] == 3
            True
            >>> v[:2]
            (1.0, 2.0)
        """
        if key in (0, "x"):
            return self.x
        if key in (1, "y"):
            return self.y
        if key in (2, "z"):
            return self.z
        if isinstance(key, slice):
            return tuple(self[i] for i in range(*key.indices(len(self))))
        msg = "Vector of length 3. The index '{}' is invalid."
        raise IndexError(msg.format(key))

    def __setitem__(self, key, value):
        if key in (0, "x"):
            self.x = value
        elif key in (1, "y"):
            self.y = value
        elif key in (2, "z"):
            self.z = value
        elif isinstance(key, slice):
            for i, j in enumerate(range(*key.indices(len(self)))):
                self[j] = value[i]
        else:
            msg = "Vector of length 3. The index '{}' is invalid."
            raise IndexError(msg.format(key))

    # Constructor ---
    def __copy__(self):
        """Create a copy of the vector."""
        return type(self)(self.x, self.y, self.z)

    def __init__(self, x=0, y=0, z=0):
        self._vector = OpenMaya.MVector(x, y, z)

    # Class methods ---
    @classmethod
    def zero(cls):
        """Build a vector with all its components set to zero."""
        return cls(0, 0, 0)

    @classmethod
    def one(cls):
        """Build a vector with all its components set to one."""
        return cls(1, 1, 1)

    @classmethod
    def from_mvector(cls, mvector):
        """Create a vector from a maya vector."""
        return cls(mvector.x, mvector.y, mvector.z)

    # Read properties ---
    @property
    def vector(self):
        """MVector: The maya vector object."""
        return self._vector

    # Read write properties ---
    @property
    def x(self):
        """float: The x component of the vector."""
        return self.vector.x

    @x.setter
    def x(self, value):
        self.vector.x = value

    @property
    def y(self):
        """float: The y component of the vector."""
        return self.vector.y

    @y.setter
    def y(self, value):
        self.vector.y = value

    @property
    def z(self):
        """float: The z component of the vector."""
        return self.vector.z

    @z.setter
    def z(self, value):
        self.vector.z = value

    @property
    def length(self):
        """float: The length of the vector."""
        return self.vector.length()

    @length.setter
    def length(self, value):
        temp = self.normal()
        self.x = temp.x * value
        self.y = temp.y * value
        self.z = temp.z * value

    # Public methods ---
    def normal(self):
        """Normalized copy."""
        return self.from_mvector(self.vector.normal())

    def normalize(self):
        """Inplace normalization."""
        self.vector.normalize()

    def decode(self, api=False):
        """Decode the vector."""
        return self.vector if api else tuple(self)

    # Aliases ---
    magnitude = length
    cross = __xor__
    dot = __mul__
    copy = __copy__


class Matrix(object):
    """4x4 matrix."""

    def __repr__(self):
        lines = "\n".join([" ".join(["{:7.3f}"] * 4)] * 4)
        return "<Matrix \n{}\n>".format(lines.format(*self.decode(True)))

    # Type conversion ---
    def __str__(self):
        return str(self.decode(flat=True))

    # Arithmetic operators ---
    def __add__(self, matrix):
        return self.from_mmatrix(self.matrix + matrix.matrix)

    def __mul__(self, matrix):
        return self.from_mmatrix(self.matrix + matrix.matrix)

    def __sub__(self, matrix):
        return self.from_mmatrix(self.matrix + matrix.matrix)

    # Comparison operators ---
    def __eq__(self, matrix):
        return self.matrix == matrix.matrix

    def __ne__(self, matrix):
        return self.matrix != matrix.matrix

    def __ge__(self, matrix):
        return self.matrix >= matrix.matrix

    def __gt__(self, matrix):
        return self.matrix > matrix.matrix

    def __le__(self, matrix):
        return self.matrix <= matrix.matrix

    def __lt__(self, matrix):
        return self.matrix < matrix.matrix

    # Emmulate container type ---
    def __getitem__(self, key):
        if isinstance(key, tuple):
            return self.matrix.getElement(*key)
        return self.matrix[key]

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            self.matrix.setElement(*(key + (value,)))
            return
        self.matrix[key] = value

    # Constructor ---
    def __init__(self, *values):
        if values:
            values = [values]
        self._matrix = OpenMaya.MMatrix(*values)

    @property
    def transform(self):
        """MTransformationMatrix: The maya transformation matrix."""
        return OpenMaya.MTransformationMatrix(self.matrix)

    # Class methods ---
    @classmethod
    def from_mmatrix(cls, mmatrix):
        """Create a matrix from a maya matrix."""
        return cls(*list(mmatrix))

    @classmethod
    def identity(cls):
        """Create a identity matrix."""
        return cls.from_mmatrix(OpenMaya.MMatrix.kIdentity)

    @classmethod
    def compose(cls, translate=Vector(), rotate=Vector(), scale=Vector.one()):
        """Compose a matrix from translate, rotate and scale value."""

    # Read properties ---
    @property
    def matrix(self):
        """MMatrix: The maya matrix."""
        return self._matrix

    # Read write methods properties ---
    @property
    def translate(self):
        """Vector: The translation component."""
        return Vector.from_mvector(self.transform.translation(Space.WORLD))

    @translate.setter
    def translate(self, value):
        srt = self.transform.setTranslation(value.vector, Space.WORLD)
        self._matrix = srt.asMatrix()

    # Public methods ---
    def decompose(self):
        """Decompose matrix into translate, rotate and scale value."""

    def inverse(self):
        """Inverted copy of the matrix.

        Returns:
            Matrix: The inverted matrix.
        """
        return self.from_mmatrix(self.matrix.inverse())

    def decode(self, flat=False):
        """Decode the matrix into a two-dimensional array.

        Arguments:
            flat (bool): Flatten the result into a single-dimensional array.

        Returns:
            tuple: The decoded matrix.
        """
        matrix = []
        for i in range(4):
            values = tuple(self.matrix.getElement(i, j) for j in range(4))
            if flat:
                matrix.extend(values)
            else:
                matrix.append(values)
        return tuple(matrix)

    def asrotate(self):
        """Create a matrix with the rotate component."""
        self.from_mmatrix(self.transform.asRotateMatrix())

    def asscale(self):
        """Create a matrix with the scale component."""
        self.from_mmatrix(self.transform.asScaleMatrix())

    # Aliases ---
    __neg__ = inverse


class EulerRotation(object):
    """3D rotation."""

    XYZ = OpenMaya.MEulerRotation.kXYZ
    YZX = OpenMaya.MEulerRotation.kYZX
    ZXY = OpenMaya.MEulerRotation.kZXY
    XZY = OpenMaya.MEulerRotation.kXZY
    YXZ = OpenMaya.MEulerRotation.kYXZ
    ZYX = OpenMaya.MEulerRotation.kZYX

    def __init__(self, x=0, y=0, z=1, order=XYZ):
        self._rotation = OpenMaya.MEulerRotation(x, y, z, order)

    @classmethod
    def from_meuler_rotation(cls, rotation):
        """Create a euler rotation from a maya euler rotation."""
        return cls(rotation.x, rotation.y, rotation.z, rotation.order)


class Quaternion(object):
    """Quaternion math."""

    def __init__(self, x=0, y=0, z=0, w=1):
        self._quaternion = OpenMaya.MQuaternion(x, y, z, w)

    @classmethod
    def from_mquaternion(cls, mquaternion):
        """Create a quaternion from a maya quaternion."""
        return cls(mquaternion.x, mquaternion.y, mquaternion.z, mquaternion.w)


# Utilities
def _match_filter(node, filter, strict=False):
    """Check if the node fit with the specified filter."""
    return filter is None or node.istype(filter, strict)


def _wrap(func, *args, **kwargs):
    """To do."""

    def _convert(func_, obj):
        try:
            return func_(obj)
        except BaseException:
            return obj

    # First, decode each arguments
    args_ = [_convert(decode, x) for x in args]
    kwargs_ = {k: _convert(decode, v) for k, v in kwargs.items()}

    # Execute the function
    returned = func(*args_, **kwargs_)
    if isinstance(returned, OpenMaya.MSelectionList):
        returned = returned.getSelectionStrings()

    # Finally encode the returned object(s)
    if isinstance(returned, _STRING_TYPES):
        return _convert(encode, returned)
    if isinstance(returned, (list, tuple, set)):
        return type(returned)(_convert(encode, x) for x in returned)
    return returned


# MIT License

# Copyright (c) 2022 Fabien Taxil

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
