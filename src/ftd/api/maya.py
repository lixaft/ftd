# pylint: disable=protected-access
"""Pythonic api for Autodesk Maya."""
from __future__ import absolute_import, division

import abc
import contextlib
import copy
import logging
import math
import sys

from maya import cmds
from maya.api import OpenMaya

__all__ = [
    # enum
    "Space",
    # common
    "encode",
    "decode",
    "wrap",
    "clear",
    "newscene",
    # node
    "DependencyNode",
    "DagNode",
    "Set",
    "ls",
    "selected",
    # create
    "LocatorCreator",
    "CurveCreator",
    "create",
    "exists",
    "delete",
    # name
    "Name",
    # plug
    "Plug",
    "connect",
    "disconnect",
    # attribute
    "Long",
    "Double",
    "Double3",
    "Boolean",
    "Enum",
    "Divider",
    "String",
    "Compound",
    "addattr",
    "hasattr_",
    "delattr_",
    # datatype
    "Point",
    "Vector",
    "Matrix",
    "EulerRotation",
    "Quaternion",
    "TransformationMatrix",
    "Color",
]

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


# General
ExistsError = type("ExistsError", (Exception,), {})


class Space(OpenMaya.MSpace):
    """Space transformation identifiers."""

    TRANSFORM = OpenMaya.MSpace.kTransform
    PRE_TRANSFORM = OpenMaya.MSpace.kPreTransform
    POST_TRANSFORM = OpenMaya.MSpace.kPostTransform
    WORLD = OpenMaya.MSpace.kWorld
    OBJECT = OpenMaya.MSpace.kObject


class Fn(OpenMaya.MFn):
    """Maya function sets."""


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
        node = _MetaNode._node_types.get(getattr(Fn, type_), None)
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
        str: The decoded object.
    """
    LOG.debug("Decode: %s", repr(obj))

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
    _MetaNode._instances.clear()


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
        **kwargs: The keyword arguments passed to the `cmds.ls()`_ command.

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
        node (DependencyNode): The node to validate.

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
class _MetaNode(type):
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

    def __new__(mcs, name, bases, dict_):
        """Automatically register all new classes that use this metaclass."""
        node = super(_MetaNode, mcs).__new__(mcs, name, bases, dict_)
        mcs.register(node)
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
        self = super(_MetaNode, cls).__call__(mobject)
        self._handle = handle
        cls._instances[hash_] = self
        return self

    @classmethod
    def register(mcs, node):
        # pylint: disable=protected-access
        """Register a new type of node.

        This allows the encoder to know all the possibilities it has to encode
        a node to find the closest match to its original type.
        """
        mcs._node_types[node._fn_id] = node
        return node


@_add_metaclass(_MetaNode)
class DependencyNode(object):
    """A Dependency Graph (DG) node."""

    _fn_id = Fn.kDependencyNode
    _fn_set = OpenMaya.MFnDependencyNode

    def __repr__(self):
        """Return ``repr(self)``."""
        return "<{} '{}'>".format(self.__class__.__name__, self)

    def __hash__(self):
        """Support storing in :ojb:`set` and as key in :obj:`dict`

        Warnings:
            The hash comparison is made with the node name. Thus, if two
            instances refer to the same node, their hash keys will be equal
            and will overwrite each other. See exemples.

        Examples:
            >>> newscene()
            >>> a = create("transform", name="A")
            >>> b = create("transform", name="B")
            >>> data = {a: 0, b: 1}
            >>> data[a]
            0
            >>> c = encode("A")
            >>> c == a and c is a
            True
            >>> data[c] = 3
            >>> data[a]  # warning: hash(c) == hash(a)
            3
        """
        return hash(str(self))

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
        if isinstance(value, _Attribute):
            value.name = key
            value.create(self)
        else:
            self.findplug(key).write(value)

    # Constructor ---
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
    def duplicate(self, name=None):
        """Duplicate the node.

        Examples:
            >>> newscene()
            >>> node = create("transform", name="A")
            >>> node
            <DagNode 'A'>
            >>> node.duplicate(name="B")
            <DagNode 'B'>

        Arguments:
            name (str): The name of the duplicate node.

        Returns:
            DependencyNode: The duplicated node instance.
        """
        return wrap(cmds.duplicate, self, name=name)[0]

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
        wrap(cmds.delete, self)

    def addattr(self, attribute):
        """Add a new attribute to the node.

        Examples:
            >>> node = create("transform")
            >>> attribute = Double(name="foo")
            >>> node.addattr(attribute)
            >>> node.hasattr("foo")
            True

        Arguments:
            attribute (Attribute): The attribute to add.
        """
        attribute.create(self)

    def hasattr(self, attribute):
        """Check if the node contains the specified attribute.

        Examples:
            >>> node = create("transform")
            >>> node.hasattr("translateX")
            True
            >>> node.hasattr("foo")
            False

        Arguments:
            attribute (str): The attribute to check.

        Returns:
            bool: True if the node contains the attribute, False otherwise.
        """
        return self.fn.hasAttribute(attribute)

    def delattr(self, attribute):
        """Delete an attribute of the node.

        Examples:
            >>> node = create("transform")
            >>> attr = Long(name="foo")
            >>> node.addattr(attr)
            >>> node.delattr("foo")
            >>> node.hasattr("foo")
            False

        Arguments:
            attribute (str): The attribute to delete.
        """
        wrap(cmds.deleteAttr, self, attribute=attribute)

    def findplug(self, attribute):
        # pylint: disable=protected-access
        """Attempt to find a plug for the given attribute.

        Arguments:
            attribute (str): The name of the attribute to search for.

        Returns:
            Plug: The instance of the plug.

        Raises:
            ExistsError: The attribute does not exists on the node.
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

    def __len__(self):
        return self.childcount

    def __contains__(self, key):
        return self.hasattr(key)

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
        """Return the node to the root of the hierarchy in which the node is.

        Returns:
            DagNode: The root node.
        """
        return self.parent(-1)

    def parents(self):
        """Get the parents of the node.

        Examples:
            >>> newscene()
            >>> a = create("transform", name="A")
            >>> b = create("transform", name="B")
            >>> c = create("transform", name="C")
            >>> a.addchild(b)
            >>> b.addchild(c)
            >>> list(c.parents())
            [<DagNode 'B'>, <DagNode 'A'>]

        Yield:
            DagNode: The next parent node instance.
        """
        # The `parentCount` and `parent` (with an index other than 0)
        # methods seem does not to work...
        mobject = self.fn.parent(0)
        while mobject.apiType() != OpenMaya.MFn.kWorld:
            parent = encode(mobject)
            yield parent
            mobject = parent.fn.parent(0)

    def parent(self, index=1):
        """The first element of :func:`parents` method.

        Returns:
            DagNode: The parent node instance.
            index (int): The parent index to return.
        """
        parents = self.parents()
        for _ in range(index - 1):
            next(parents, None)
        return next(parents, None)

    def siblings(self):
        """Iterates on every other node at the same level as this one.

        Yield:
            DagNode: The next sibling node instance.
        """
        parent = self.parent()
        if parent is None:
            nodes = ls(assemblies=True)
        else:
            nodes = parent.children()

        for node in nodes:
            if node != self:
                yield node

    def sibling(self):
        """The first element of :func:`siblings` method.

        Returns:
            DagNode: The sibiling node instance.
        """
        return next(self.siblings(), None)

    def shapes(self):
        """Iterates on each _shapes of this node.

        Yield:
            DagNode: The next shape instance.
        """
        for index in range(self.fn.childCount()):
            mobject = self.fn.child(index)
            if mobject.hasFn(OpenMaya.MFn.kShape):
                yield encode(mobject)

    def shape(self):
        """The first element of :func:`shapes` method.

        Returns:
            DagNode: The shape node instance.
        """
        return next(self.shapes(), None)

    def children(self, filters=None, recursive=False):
        """Iterates on each child of this node.

        Examples:
            >>> newscene()
            >>> a = create("transform", name="A")
            >>> b = create("transform", name="B")
            >>> c = create("transform", name="C")
            >>> a.addchildren(b, c)
            >>> list(a.children())
            [<DagNode 'B'>, <DagNode 'C'>]

        Yield:
            DagNode: The next child instance.
        """
        for index in range(self.fn.childCount()):
            child = encode(self.fn.child(index))

            if not child.object.hasFn(OpenMaya.MFn.kTransform):
                continue

            if filters is not None:
                ntype = child.type
                if isinstance(filters, str) and ntype != filters:
                    continue
                if isinstance(filters, (list, tuple)) and ntype not in filters:
                    continue

            yield child

            if recursive:
                for each in child.children(filters, recursive=True):
                    yield each

    def child(self):
        """The first element of :func:`childrens` method.

        Returns:
            DagNode: The child node instance.
        """
        return next(self.children(), None)

    def addchild(self, node):
        """Add a child to the node.

        Examples:
            >>> newscene()
            >>> a = create("transform", name="A")
            >>> b = create("transform", name="B")
            >>> a.addchild(b)
            >>> list(a.children())
            [<DagNode 'B'>]

        Arguments:
            node (DagNode): The node to add.
        """
        node._set_parent(self)

    def addchildren(self, *args):
        """Recursively add multiple children to the node.

        Arguments:
            *args: The nodes to add as child.
        """
        for arg in args:
            if isinstance(arg, (list, tuple, set)):
                self.addchildren(*arg)
            else:
                self.addchild(arg)

    def hide(self):
        """Set the visibility plug to False."""
        self.findplug("visibility").write(False)

    def show(self):
        """Set the visibility plug to True."""
        self.findplug("visibility").write(True)

    def goto(self, target, srt="srt"):
        """Move self to the target transformation.

        Arguments:
            target (DagNode): The target transformation where self
                need to go. This value can also be a :class:`Matrix`
                or :class:`TransformationMatrix` type.
            srt (str): The attributes that must match the target.
        """
        if isinstance(target, DagNode):
            target = target["worldMatrix"][0].read()

        matrix = Matrix(target)
        matrix *= self["parentInverseMatrix"].read()
        tmatrix = TransformationMatrix(matrix)
        if "t" in srt:
            self["translate"] = tmatrix.translation()
        if "r" in srt:
            self["rotate"] = map(math.degrees, tmatrix.rotation())
        if "s" in srt:
            self["scale"] = tmatrix.scale()

    def transformation(self, space=Space.OBJECT):
        """Returns the node transformation matrix.

        Arguments:
            space (Space): The space under which the TransformationMatrix
                will be returned

        Returns:
            TransformationMatrix: The transformation matrix instance.
        """
        plug = self["worldMatrix"] if space == Space.WORLD else self["matrix"]
        return TransformationMatrix(plug.read())

    def boundingbox(self):
        """Returns the node bounding box.

        Returns:
            BoundingBox: The bounding box instance.
        """
        return BoundingBox(self.fn.boundingBox)

    # Private methods ----
    def _set_parent(self, parent):
        """Set the parent of self in the outliner."""
        wrap(cmds.parent, self, parent)


class Set(DependencyNode):
    """An object set node."""

    _fn_id = Fn.kSet
    _fn_set = OpenMaya.MFnSet

    def duplicate(self, name=None):
        new = super(Set, self).duplicate(name)
        for member in self.members():
            new.add(member)
        return new

    def add(self, node):
        """Add a new object to the set.

        Arguments:
            node (DagNode): The node to add.
        """
        wrap(cmds.sets, node, forceElement=self)

    def remove(self, node):
        """Remove a node from the set.

        Arguments:
            node (DagNode): The node to remove.
        """
        wrap(cmds.sets, node, remove=self)

    def clear(self):
        """Removes all elements from this set."""
        wrap(cmds.sets, clear=self)

    def members(self):
        """Iterates on each members of the set."""
        for member in wrap(cmds.sets, self, query=True):
            yield encode(member)


class Shape(DagNode):
    """A shape node."""

    _fn_id = Fn.kShape

    def _set_parent(self, parent):
        wrap(cmds.parent, self, parent, shape=True, relative=True)


class NurbsCurve(Shape):
    """A curve node."""

    _fn_id = Fn.kNurbsCurve
    _fn_set = OpenMaya.MFnNurbsCurve


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
        **kwargs: The keyword arguments passed to the `cmds.delete()`_ command.

    Returns:
        list: The nodes list.

    .. _cmds.delete():
        https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/CommandsPython/delete.html
    """
    return wrap(cmds.delete, *args, **kwargs)


# Create
@_add_metaclass(abc.ABCMeta)
class _Creator(object):
    """Allow the customization of node creation."""

    key = None
    """str: The key to use with :func:`create` to call the creator."""

    registered = {}
    """dict: The registered creators."""

    @classmethod
    def register(cls, creator):
        """Register a creator class to make it available in the api.

        Arguments:
            creator (class): The class to register.

        Returns:
            class: The registered class.
        """
        if issubclass(cls, _Creator):
            cls.registered[creator.key] = {"creator": creator}
        return creator

    @abc.abstractmethod
    def create(self, name=key):
        """Create the node.

        Arguments:
            name (str): The name of the node to create.

        Returns:
            DependencyNode: The created node.
        """


@_Creator.register
class LocatorCreator(_Creator):
    """Create a new locator node.

    Examples:
        >>> newscene()
        >>> create("locator")
        <DagNode 'locator'>
    """

    key = "locator"

    def create(self, name=key):
        return wrap(cmds.spaceLocator, name=name)[0]


@_Creator.register
class CurveCreator(_Creator):
    """Create a new Non-Uniform Rational Basis Splines (NURBS) curve node.

    Examples:
        >>> creator = CurveCreator(degree=1, close=True)
        >>> creator.points.append((0, 0, 0))
        >>> creator.points.append((0, 5, 0))
        >>> creator.points.append((5, 5, 0))
        >>> creator.points.append((5, 0, 0))
        >>> creator.create("square")
        <DagNode 'square'>
    """

    key = "curve"

    def __init__(self, points=None, degree=1, close=False, knots=None):
        self._points = points or []
        self._degree = degree
        self._close = close
        self._knots = knots
        self._connect = False

    def create(self, name=key):
        points = []
        for point in self.points:
            if isinstance(point, Plug):
                points.append(point.read())
            else:
                points.append(point)
        flags = {}

        if self.close:
            if points[: self.degree] != points[-self.degree]:
                points += points[: self.degree]
            if self.knots is None:
                length = len(points) + self.degree - 1
                flags["knot"] = self.knots or range(length)

        flags["name"] = name
        flags["point"] = points
        flags["degree"] = self.degree
        flags["periodic"] = self.close
        node = wrap(cmds.curve, **flags)
        node.shape().name = node + "Shape"

        if self.connect:
            for index, point in enumerate(self.points):
                if isinstance(point, Plug):
                    point.connect(node.shape()["controlPoints"][index])

        return node

    # property (RW)
    @property
    def points(self):
        """list: A list of points for each curve cvs."""
        return self._points

    @points.setter
    def points(self, value):
        self._points = value

    @property
    def degree(self):
        """int: The degree of the curve.

        A number of points (degree + 1) is required to create a visible curve.
        """
        return self._degree

    @degree.setter
    def degree(self, value):
        self._degree = value

    @property
    def close(self):
        """bool:"""
        return self._close

    @close.setter
    def close(self, value):
        self._close = value

    @property
    def knots(self):
        """list:

        If it not specified, a array will be automaticaly generated during
        the execution of :func:`create`.
        """
        return self._knots

    @knots.setter
    def knots(self, value):
        self._knots = value

    @property
    def connect(self):
        """bool:"""
        return self._connect

    @connect.setter
    def connect(self, value):
        self._connect = value


@_Creator.register
class ControlCreator(CurveCreator):
    """Create a new control."""

    key = "control"


def create(type, name=None, **kwargs):
    # pylint: disable=redefined-builtin
    """Create a new node.

    This function allows to modify the creation of nodes by adding types or
    replacing existing ones. If a type is known to :obj:`Creator.registered`,
    then the associated creator will be used in the creation. See the
    documentation of the :class:`Creator` class for more details.

    Examples:
        >>> newscene()
        >>> create("addDoubleLinear")
        <DependencyNode 'addDoubleLinear'>
        >>> a = create("transform", name="A")
        >>> a
        <DagNode 'A'>
        >>> b = create("transform", name="B", parent=a)
        >>> b.path
        '|A|B'

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
    if isinstance(name, Name):
        name = name.decode()
    if type in _Creator.registered:
        type = _Creator.registered[type]["creator"](**kwargs)

    if isinstance(type, _Creator):
        return type.create(name or type.key)

    return wrap(cmds.createNode, type, name=name or type, **kwargs)


# Name
class Name(object):
    """Improves the creation and modification of node names.

    A name is represented by a list of tokens. During the decoding process,
    each token will be added with the next one by adding a :obj:`SEPARATOR`.

    Examples:
        >>> name = Name("my", "node")
        >>> name.decode()
        'my_node'

    Arguments:
        *args: The initial tokens that represented the name.

            Different form are accepted::

                Name("my", "node")
                Name(["my", "node"])
                Name("my_node")
    """

    SEPARATOR = "_"
    """str: The character used to split or join the :obj:`tokens`."""

    TYPES = {
        "transform": "grp",
        "control": "ctrl",
        "locator": "loc",
        "mesh": "msh",
    }

    def __repr__(self):
        return "<Name '{}'>".format(self.decode())

    # conversion
    def __str__(self):
        return self.decode()

    # arithmetic operator
    def __add__(self, other):
        if isinstance(other, Name):
            other = other._tokens
        return Name(self._tokens + other)

    # augmented assignment
    __iadd__ = __add__

    # logical operators
    def __eq__(self, other):
        if isinstance(other, Name):
            other = other._tokens
        return self._tokens == other

    def __ne__(self, other):
        if isinstance(other, Name):
            other = other._tokens
        return self._tokens != other

    # container type
    def __getitem__(self, index):
        return self._tokens[index]

    def __setitem__(self, index, value):
        self._tokens[index] = value
        self.rename()

    def __delitem__(self, index):
        del self._tokens[index]
        self.rename()

    def __iter__(self):
        return iter(self._tokens)

    def __contains__(self, value):
        return value in self._tokens

    def __len__(self):
        return len(self._tokens)

    # constructor
    def __init__(self, *args):
        self._node = None
        self._tokens = []
        self._parse(args)

    # public
    def decode(self):
        """Return a string representation of the name with :obj:`SEPARATOR`.

        The ``__str__`` or ``str()`` method do exactly the same thing.

        Examples:
            >>> name = Name("my", "node", ["srt"])
            >>> name.decode()
            'my_node_srt'
            >>> name.decode() == str(name)
            True

        Returns:
            str: The full name as a string.
        """
        return self.SEPARATOR.join(self._tokens)

    def append(self, token):
        """Append a token to the end.

        Examples:
            >>> name = Name("my_node")
            >>> name.append("name")
            >>> name.decode()
            'my_node_name'

        Arguments:
            token (str): The token to be added at the end of the list.
        """
        self._tokens.append(token)
        self.rename()

    def extend(self, tokens):
        """Extend list by appending elements from the iterable.

        Examples:
            >>> name = Name("my_node")
            >>> name.extend(["name", "grp"])
            >>> name.decode()
            'my_node_name_grp'

        Arguments:
            tokens (list): The iterable to be added at the end of the list.
        """
        self._tokens.extend(tokens)
        self.rename()

    def insert(self, index, token):
        """Insert object before index.

        Examples:
            >>> name = Name("my_node")
            >>> name.insert(1, "great")
            >>> name.decode()
            'my_great_node'

        Arguments:
            index (int): The index where the element needs to be inserted.
            token (str): The token to be inserted in the list.
        """
        self._tokens.insert(index, token)
        self.rename()

    def remove(self, token):
        """Remove first occurrence of value.

        Examples:
            >>> name = Name("my_node_name")
            >>> name.remove("node")
            >>> name.decode()
            'my_name'

        Arguments:
            token (str): The token to be removed from the list.
        """
        self._tokens.remove(token)
        self.rename()

    def pop(self, index=-1):
        """Remove and return item at index.

        Examples:
            >>> name = Name("node_grp")
            >>> name.pop()
            >>> name.decode()
            'node'

        Arguments:
            index (int): The index to removed from the list.
        """
        self._tokens.pop(index)
        self.rename()

    def replace(self, old, new):
        """Replace all the matching token from the list.

        Examples:
            >>> name = Name("my_useless_node")
            >>> name.replace("useless", "useful")
            >>> name.decode()
            'my_useful_node'

        Arguments:
            old (str): The token to be replaced from the list.
            new (str): The token that will replace the old one.
        """
        for key, token in enumerate(self._tokens):
            if token == old:
                self._tokens[key] = new
        self.rename()

    def addtype(self):
        """Append the node type as suffix."""
        # find the type by querying the node.
        if isinstance(self.node, DagNode):
            nodetype = (self.node.shape() or self.node).type
        elif isinstance(self.node, DependencyNode):
            nodetype = self.node.type
        else:
            LOG.error("No node associated to the name.")
            return

        suffix = self.TYPES.get(nodetype, nodetype)
        if self.suffix != suffix:
            self.append(suffix)
        self.rename()

    def rename(self):
        """Rename the associated node.

        Normally it should not be necessary to call it, it is called
        automatically each time the tokens are modified.
        """
        LOG.debug("Rename: '%s' to '%s'", self.node, self)
        if self.node is None:
            return
        wrap(cmds.rename, self.node, self)

    def copy(self):
        """Create and return a deep copy of the instance.

        Examples:
            >>> name_a = Name("my_node")
            >>> name_b = name_a.copy()
            >>> name_a.tokens is name_b.tokens
            False

        Returns:
            Name: The copied instance.
        """
        return Name(list(self._tokens))

    def isunique(self):
        """Make sure the name does not exist twice in the current scene.

        Returns:
            bool: True if the name is unique, otherwise False.
        """
        return not wrap(cmds.objExists, self)

    # private
    def _parse(self, tokens):
        """Parse the passed value and fill in the class tokens."""
        for token in tokens:
            if isinstance(token, (list, tuple, set)):
                self._parse(token)
            elif isinstance(token, _STRING_TYPES) and self.SEPARATOR in token:
                self._tokens.extend(token.split(self.SEPARATOR))
            else:
                self._tokens.append(str(token))

    # property (R)
    @property
    def tokens(self):
        """list: The list of tokens that compose the name.

        Examples:
            >>> name = Name("my_node")
            >>> name.tokens
            ['my', 'node']
        """
        return self._tokens

    @property
    def node(self):
        """DependencyNode: The associated node instance."""
        return self._node

    # property (RW)
    @property
    def prefix(self):
        """str: The first token of the list.

        Examples:
            >>> name = Name("my_node")
            >>> name.prefix
            'my'
            >>> name.prefix = "a"
            >>> str(name)
            'a_node'
        """
        return self._tokens[0]

    @prefix.setter
    def prefix(self, value):
        self._tokens[0] = value
        self.rename()

    @property
    def suffix(self):
        """str: The last token of the list.

        Examples:
            >>> name = Name("my_node")
            >>> name.suffix
            'node'
            >>> name.suffix = "name"
            >>> str(name)
            'my_name'
        """
        return self._tokens[-1]

    @suffix.setter
    def suffix(self, value):
        self._tokens[-1] = value
        self.rename()


# Plug
class Plug(object):
    """Plug object."""

    def __repr__(self):
        return "<Plug '{}' {}>".format(self, self.read())

    # conversion
    def __str__(self):
        return self.plug.name()

    def __int__(self):
        return int(self.read())

    def __float__(self):
        return float(self.read())

    def __bool__(self):
        return bool(self.read())

    # python 2/3 compatibility
    __nonzero__ = __bool__

    # unary operator
    def __pos__(self):
        return +self.read()

    def __neg__(self):
        return -self.read()

    def __abs__(self):
        """Returns the absolute value of self.

        Examples:
            >>> node = create("transform")
            >>> node["translateX"] = -3
            >>> abs(node["translateX"])
            3.0
        """
        return abs(self.read())

    def __round__(self, ndigits=0):
        """Returns a float number rounded to the specified number of decimals.

        Examples:
            >>> node = create("transform")
            >>> node["translateX"] = 0.12345
            >>> round(node["translateX"], ndigits=2)
            0.12
        """
        return round(self.read(), ndigits)

    def __ceil__(self):
        """Returns the smallest integer greater than or equal to self.

        Examples:
            >>> import math
            >>> node = create("transform")
            >>> node["translateX"] = 0.1
            >>> math.ceil(node["translateX"])
            1
        """
        return math.ceil(self.read())

    def __floor__(self):
        """Returns the largest integer less than or equal to self.

        Examples:
            >>> import math
            >>> node = create("transform")
            >>> node["translateX"] = 0.1
            >>> math.floor(node["translateX"])
            0
        """
        return math.floor(self.read())

    def __trunc__(self):
        """Returns the value of self trunced to an integer.

        In other words, remove the decimal part.

        Examples:
            >>> import math
            >>> node = create("transform")
            >>> node["translateX"] = 0.1
            >>> math.trunc(node["translateX"])
            0
        """
        return math.trunc(self.read())

    # arithmetic operator
    def __add__(self, other):
        return self.read() + _read(other)

    def __sub__(self, other):
        return self.read() - _read(other)

    def __mul__(self, other):
        return self.read() * _read(other)

    def __truediv__(self, other):
        return self.read() / _read(other)

    def __floordiv__(self, other):
        self.disconnect(other)

    def __mod__(self, other):
        return self.read() % _read(other)

    def __pow__(self, other, modulo=None):
        return pow(self.read(), _read(other), modulo)

    def __divmod__(self, other):
        """Returns the quotient and the remainder of self and other.

        Examples:
            >>> node = create("transform")
            >>> node["translateX"] = 10
            >>> divmod(node["translateX"], 3)
            (3.0, 1.0)
        """
        return divmod(self.read(), _read(other))

    # reflected arithmetic operator
    def __radd__(self, other):
        return _read(other) + self.read()

    def __rsub__(self, other):
        return _read(other) - self.read()

    def __rmul__(self, other):
        return _read(other) * self.read()

    def __rtruediv__(self, other):
        return _read(other) / self.read()

    def __rmod__(self, other):
        return _read(other) % self.read()

    def __rpow__(self, other, modulo=None):
        return pow(_read(other), self.read(), modulo)

    def __rdivmod__(self, other):
        return divmod(_read(other), self.read())

    # augmented assignment
    __iadd__ = __add__
    __isub__ = __sub__
    __imul__ = __mul__
    __itruediv__ = __truediv__
    __imod__ = __mod__
    __ipow__ = __pow__

    # comparison operator
    def __eq__(self, other):
        return self.read() == _read(other)

    def __ne__(self, other):
        return self.read() != _read(other)

    def __ge__(self, other):
        return self.read() >= _read(other)

    def __gt__(self, other):
        return self.read() > _read(other)

    def __le__(self, other):
        return self.read() <= _read(other)

    def __lt__(self, other):
        return self.read() < _read(other)

    # bitwise operator
    def __lshift__(self, other):
        other.connect(self)
        return self

    def __rshift__(self, other):
        self.connect(other)
        return self

    # container type
    def __len__(self):
        return self.childcount

    def __getitem__(self, key):
        return self.findchild(key)

    def __setitem__(self, key, value):
        self[key].write(value)

    def __contains__(self, key):
        return self.haschild(key)

    def __iter__(self):
        return self.children()

    # constructor
    def __init__(self, mplug):
        self._plug = mplug
        self._node = None

    # Read properties ---
    @property
    def plug(self):
        """MPlug: The mplug instance of the plug."""
        return self._plug

    @property
    def node(self):
        """Get the associated node."""
        return self._node

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
        return wrap(cmds.getAttr, self, type=True)

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
        """Query the value of the plug."""
        return self.read()

    @value.setter
    def value(self, value):
        self.write(value)

    @property
    def keyable(self):
        """Return if the plug appair in the keyable or not."""
        return self.plug.isKeyable

    @keyable.setter
    def keyable(self, value):
        if self.iscompound:
            for child in self.children():
                child.keyable = value
        else:
            wrap(cmds.setAttr, self, keyable=value)

    @property
    def channelbox(self):
        """Return if the plug appair in the channelbox or not."""
        return self.plug.isChannelBox

    @channelbox.setter
    def channelbox(self, value):
        if self.iscompound:
            for child in self.children():
                child.channelbox = value
        else:
            wrap(cmds.setAttr, self, channelBox=value)

    @property
    def lock(self):
        """bool: the locked state of the plug."""
        return self.plug.isLocked

    @lock.setter
    def lock(self, value):
        if self.iscompound:
            for child in self.children():
                child.lock = value
        else:
            wrap(cmds.setAttr, self, lock=value)

    @property
    def default(self):
        """any: The plug is default value."""
        value = wrap(
            cmds.attributeQuery,
            self.attribute,
            node=self.node,
            listDefault=True,
        )
        if isinstance(value, (list, tuple)) and len(value) == 1:
            value = value[0]
        return value

    @default.setter
    def default(self, value):
        cmds.addAttr(self.name, edit=True, defaultValue=value)

    # Public methods ---
    def read(self):
        """Query the value of the plug."""
        return cmds.getAttr(self.name)

    def write(self, value):
        """Set the value of the plug."""
        cmds.setAttr(self.name, value)

    def hide(self):
        """Hide the attribute."""
        self.keyable = False
        self.channelbox = False

    def show(self):
        """Show the attribute."""
        self.channelbox = True

    def reset(self):
        """Reset the value to it's default.

        Examples:
            >>> node = create("transform")
            >>> node["scaleX"] = 10
            >>> node["scaleX"].reset()
            >>> node["scaleX"].read()
            1.0
        """
        self.write(self.default)

    def public(self):
        """Expose the attribute in the channel-box."""
        self.show()
        self.keyable = True

    def private(self):
        """Lock and hide the attribute."""
        self.lock = True
        self.hide()

    def connect(self, other):
        """Connect a plug to another one.

        Examples:
            >>> newscene()
            >>> node = create("transform")
            >>> node["translateX"].connect(node["translateY"])
            >>> node["translateY"].input()
            <Plug 'transform.translateX' 0.0>

        Arguments:
            other (Plug): The other plug to connect.
        """
        wrap(cmds.connectAttr, self, other)

    def disconnect(self, other):
        """Disconnect a plug to another one.

        Examples:
            >>> newscene()
            >>> node = create("transform")
            >>> node["translateX"].connect(node["translateY"])
            >>> node["translateY"].input()
            <Plug 'transform.translateX' 0.0>
            >>> node["translateX"].disconnect(node["translateY"])
            >>> node["translateY"].input()

        Arguments:
            other (Plug): The other plug to disconnect.
        """
        wrap(cmds.disconnectAttr, self, other)

    def inputs(self):
        """The plug connected as input.

        Yields:
            Plug: The input plug instance.
        """
        for plug in self._connections(source=True):
            yield plug

    def input(self):
        """The plug connected as input.

        Returns:
            Plug: The input plug instance.
        """
        return next(self.inputs(), None)

    def outputs(self):
        """The plug connected as output.

        Yield:
            Plug: The next output plug instance.
        """
        for plug in self._connections(destination=True):
            yield plug

    def output(self):
        """The first output plug.

        Returns:
            Plug: The plug instance.
        """
        return next(self.outputs(), None)

    def findchild(self, attribute):
        """Find a child plug.

        Examples:
            >>> newscene()
            >>> node = create("transform")
            >>> node["translate"].findchild(0)
            <Plug 'transform.translateX' 0.0>

        Arguments:
            attribute (str, int, slice): The child attribute to find.

        Returns:
            Plug: The child plug instance.

        Raises:
            RuntimeError: The plug does not exist.
        """
        if isinstance(attribute, int):
            if attribute < 0:
                attribute = self.childcount - abs(attribute)
            if self.isarray:
                mplug = self.plug.elementByLogicalIndex(attribute)
                return Plug(mplug)
            if self.iscompound:
                return Plug(self.plug.child(attribute))

        elif isinstance(attribute, _STRING_TYPES):
            for index in range(self.childcount):
                mplug = self.plug.child(index)
                nshort = mplug.partialName()
                nlong = mplug.partialName(useLongNames=True)
                if attribute in [x.split(".")[-1] for x in (nshort, nlong)]:
                    return Plug(mplug)

        elif isinstance(attribute, slice):
            indices = attribute.indices(self.childcount)
            return map(self.findchild, range(*indices))

        raise RuntimeError("Child not found.")

    def haschild(self, attribute):
        """Check if the plug has the specified has a child.

        Examples:
            >>> node = encode("transform")
            >>> node["translate"].haschild("foo")
            False
            >>> node["translate"].haschild(0)
            True

        Arguments:
            attribute (str, int): The attribute to check.

        Returns:
            bool: True if the attribute is a child to self, False otherwise.
        """
        try:
            self.findchild(attribute)
            return True
        except RuntimeError:
            return False

    def children(self):
        """Iterates on each children of this plug.

        Examples:
            >>> newscene()
            >>> node = create("transform")
            >>> for child in node["translate"].children():
            ...     child
            <Plug 'transform.translateX' 0.0>
            <Plug 'transform.translateY' 0.0>
            <Plug 'transform.translateZ' 0.0>

        Yield:
            Plug: The child plug instance.
        """
        for index in range(self.childcount):
            yield self.findchild(index)

    # private
    def _connections(self, source=False, destination=False):
        """List the conections of the plug."""
        plugs = wrap(
            cmds.listConnections,
            self,
            source=source,
            destination=destination,
            plugs=True,
        )
        for plug in plugs or []:
            yield encode(plug)


def _read(value):
    """Returns a value, whether the object is a plug or not."""
    if isinstance(value, Plug):
        return value.read()
    return value


def connect(*args, **kwargs):
    """Connect two plug."""
    wrap(cmds.connectAttr, *args, **kwargs)


def disconnect(*args, **kwargs):
    """Sisconnect two plug."""
    wrap(cmds.disconnectAttr, *args, **kwargs)


# Attributes
@_add_metaclass(abc.ABCMeta)
class _Attribute(object):
    """Base class for creating new attribute.

    Examples:
        >>> newscene()
        >>> node = create("transform")
        >>> attribute = Double("myAttr")
        >>> node.addattr(attribute)

        This api also provides a shorter synthax to add new attributes:

        >>> node = create("transform")
        >>> node["myAttr"] = Double()

    Arguments:
        name (str): The name of the attribute.
        array (bool): Whether the attribute is to have an array of data
    """

    type = None
    _typeflag = "attributeType"

    def __init__(self, name=None, array=False):
        self._name = name
        self._array = array

    # public
    def create(self, node, **kwargs):
        """Create the attribute."""
        self._addflag(kwargs, self._typeflag, self.type)
        self._addflag(kwargs, "longName", self.name)
        self._addflag(kwargs, "multi", self.array)
        wrap(cmds.addAttr, node, **kwargs)

    # private
    @staticmethod
    def _addflag(kwargs, key, value):
        """Add a flag to the specified dictionary.

        Only add the flag if it has a valid value. Maya seems to dislike
        some "empty" flags even with a value of None.

        If the flag already exists, keep the existing one.
        """
        if value is not None:
            kwargs.setdefault(key, value)

    # property (RW)
    @property
    def name(self):
        """str: The name of the attribute to create."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def array(self):
        """bool: Create an array/simple attribute."""
        return self._array

    @array.setter
    def array(self, value):
        self._array = value


@_add_metaclass(abc.ABCMeta)
class _Numeric(_Attribute):
    # pylint: disable=redefined-builtin
    """Base class for creating numerical attributes."""

    def __init__(self, name=None, value=None, min=None, max=None, array=False):
        super(_Numeric, self).__init__(name, array)
        self._value = value
        self._min = min
        self._max = max

    def create(self, node, **kwargs):
        self._addflag(kwargs, "defaultValue", self.value)
        self._addflag(kwargs, "minValue", self.min)
        self._addflag(kwargs, "maxValue", self.max)
        super(_Numeric, self).create(node, **kwargs)

    # property (RW)
    @property
    def value(self):
        """int or float: The default value that the attribute should take."""
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    @property
    def min(self):
        """any: The minimum value that the attribute can take."""
        return self._min

    @min.setter
    def min(self, value):
        self._min = value

    @property
    def max(self):
        """any: The maximum value that the attribute can take."""
        return self._max

    @max.setter
    def max(self, value):
        self._max = value


class Long(_Numeric):
    """Long attribute."""

    type = "long"


class Double(_Numeric):
    """Double attribute."""

    type = "double"


class Double3(_Numeric):
    """Double 3 attribute."""

    type = "double3"

    def create(self, node, **kwargs):
        with _restore(self):
            self.value = None
            super(Double3, self).create(node, **kwargs)

        # make a copy of the value to modify it if necessary
        value = self.value
        if isinstance(value, (int, float)):
            value = [value] * 3

        # create the children attributes
        children_kwargs = kwargs.copy()
        children_kwargs.pop("parent", None)
        for index, axis in enumerate("XYZ"):
            child = Double(name=self.name + axis, value=value[index])
            child.create(node, parent=self.name, **children_kwargs)


class Boolean(_Numeric):
    """Boolean attribute."""

    type = "bool"


class Enum(_Attribute):
    """Enumerated attribute."""

    type = "enum"

    def __init__(self, name=None, enum=None, value=None, array=False):
        super(Enum, self).__init__(name, array)
        self._enum = enum or []
        self._value = value

    def create(self, node, **kwargs):
        self._addflag(kwargs, "defaultValue", self.value)
        self._addflag(kwargs, "enumName", ":".join(self.enum))
        super(Enum, self).create(node, **kwargs)

    # property (RW)
    @property
    def enum(self):
        """list: A list the containt the enum values."""
        return self._enum

    @enum.setter
    def enum(self, value):
        if isinstance(value, _STRING_TYPES):
            value = value.split(":")
        self._enum = value

    @property
    def value(self):
        """int or float: The default value that the attribute should take."""
        return self._value

    @value.setter
    def value(self, value):
        self._value = value


class Divider(Enum):
    """Divider attribute."""

    def __init__(self, name=None, label=None):
        super(Divider, self).__init__(name)
        self._label = label

    def create(self, node, **kwargs):
        with _restore(self):
            if self.label is None:
                self.label = self.name

            self._addflag(kwargs, "enumName", self.label)
            self._addflag(kwargs, "niceName", " ")
            super(Divider, self).create(node, **kwargs)
            node.findplug(self.name).show()

    # property (RW)
    @property
    def label(self):
        """str: The label of the divider."""
        return self._label

    @label.setter
    def label(self, value):
        self._label = value


class String(_Attribute):
    """String attribute."""

    type = "string"
    _typeflag = "dataType"


class MatrixAttribute(_Attribute):
    """Matrix attribute"""

    type = "matrix"


class Message(_Attribute):
    """Message attribute.

    A message attribute does not do anything except formally declare a
    relationships between nodes.
    """

    type = "message"


class Compound(_Attribute):
    """Compound attribute."""

    type = "compound"

    def __init__(self, name=None, children=None, array=False):
        super(Compound, self).__init__(name, array)
        self.children = children or []
        self.array = array

    def add(self, attribute):
        """Add a new child to the compound."""
        self.children.append(attribute)

    def create(self, node, **kwargs):
        kwargs.setdefault("attributeType", self.type)
        kwargs.setdefault("numberOfChildren", len(self.children))
        super(Compound, self).create(node, **kwargs)
        for child in self.children:
            child.create(node, parent=self.name)


def addattr(node, attribute):
    """Add a new attribute."""
    node.addattr(attribute)
    return node[attribute]


def hasattr_(node, attribute):
    """Check if a node has an attribute."""
    return node.hasattr(attribute)


def delattr_(node, attribute):
    """Delete the given attribute on the node."""
    node.delattr(attribute)


# Mathematica
class Point(OpenMaya.MPoint):
    """This class provides an implementation of a point."""

    def __repr__(self):
        return "<Point {}>".format(self)

    # arithmetic operator
    def __add__(self, other):
        return encode(super(Point, self).__add__(other))

    def __mul__(self, other):
        return encode(super(Point, self).__mul__(other))

    def __sub__(self, other):
        return encode(super(Point, self).__sub__(other))

    def __truediv__(self, other):
        return encode(super(Point, self).__truediv__(other))

    # reflected arithmetic operator
    def __radd__(self, other):
        return encode(super(Point, self).__radd__(other))

    def __rmul__(self, other):
        return encode(super(Point, self).__rmul__(other))

    def __rsub__(self, other):
        return encode(super(Point, self).__rsub__(other))

    def __rtruediv__(self, other):
        return encode(super(Point, self).__rtruediv__(other))

    # constructor
    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], Plug):
            super(Point, self).__init__(args[0].read())
        else:
            super(Point, self).__init__(*args, **kwargs)

    # public
    def decode(self):
        """Decode the point into a four elements tuple."""
        return tuple(self)


class Vector(OpenMaya.MVector):
    # pylint: disable=invalid-name
    """Allow vectors to be handled easily."""

    def __repr__(self):
        return "<Vector {}>".format(self)

    # arithmetic operator
    def __add__(self, other):
        return encode(super(Vector, self).__add__(other))

    def __mul__(self, other):
        return encode(super(Vector, self).__mul__(other))

    def __sub__(self, other):
        return encode(super(Vector, self).__sub__(other))

    def __truediv__(self, other):
        return encode(super(Vector, self).__truediv__(other))

    # reflected arithmetic operator
    def __radd__(self, other):
        return encode(super(Vector, self).__radd__(other))

    def __rmul__(self, other):
        return encode(super(Vector, self).__rmul__(other))

    def __rsub__(self, other):
        return encode(super(Vector, self).__rsub__(other))

    def __rtruediv__(self, other):
        return encode(super(Vector, self).__rtruediv__(other))

    # bitwise operator
    def __xor__(self, other):
        return encode(super(Vector, self).__xor__(other))

    # reflected bitwise operators
    def __rxor__(self, other):
        return encode(super(Vector, self).__rxor__(other))

    # constructor
    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], Plug):
            super(Vector, self).__init__(args[0].read())
        else:
            super(Vector, self).__init__(*args, **kwargs)

    # public
    def decode(self):
        """Decode the vector into a three elements tuple."""
        return tuple(self)

    def normal(self):
        """Create a new vector containing the normalized version of this one.

        Returns:
            Vector: The normalized vector.
        """
        return encode(super(Vector, self).normal())

    def rotateBy(self, *args, **kwargs):
        """The vector resulting from rotating this one by the given amount."""
        return encode(super(Vector, self).rotateBy(*args, **kwargs))

    def rotateTo(self, target):
        """Returns the quaternion which will rotate this vector into another.

        Arguments:
            target (Vector): The target vector.

        Returns:
            Quaternion: The resulting quaternion.
        """
        return encode(super(Vector, self).rotateTo(target))

    def transformAsNormal(self, matrix):
        """Treats the vector as a normal vector.

        Arguments:
            matrix (Matrix): The transformation matrix.

        Returns:
            Vector: The resulting transformed vector.
        """
        return encode(super(Vector, self).transformAsNormal(matrix))


class Matrix(OpenMaya.MMatrix):
    """A matrix math class for 4x4 matrices of doubles."""

    def __repr__(self):
        return "<Matrix \n{}\n>".format(self)

    # conversion
    def __str__(self):
        return (("{:7.2f} " * 4 + "\n") * 4).format(*self.decode(True))[:-1]

    # unary operator
    def __pos__(self):
        return self

    def __neg__(self):
        return self

    # arithmetic operator
    def __add__(self, other):
        return encode(super(Matrix, self).__add__(_read(other)))

    def __mul__(self, other):
        return encode(super(Matrix, self).__mul__(_read(other)))

    def __sub__(self, other):
        return encode(super(Matrix, self).__sub__(_read(other)))

    # reflected arithmetic operator
    def __radd__(self, other):
        return encode(super(Matrix, self).__radd__(_read(other)))

    def __rmul__(self, other):
        return encode(super(Matrix, self).__rmul__(_read(other)))

    def __rsub__(self, other):
        return encode(super(Matrix, self).__rsub__(_read(other)))

    # container type
    def __getitem__(self, key):
        if isinstance(key, tuple):
            return self.getElement(*key)
        return super(Matrix, self).__getitem__(key)

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            return self.setElement(*(key + (value,)))
        return super(Matrix, self).__setitem__(key, value)

    # constructor
    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], Plug):
            super(Matrix, self).__init__(args[0].read())
        else:
            super(Matrix, self).__init__(*args, **kwargs)

    # public
    def decode(self, flat=False):
        """Decode the matrix into a two-dimensional array.

        Arguments:
            flat (bool): Flatten the result into a single-dimensional array.

        Returns:
            list: The decoded matrix.
        """
        mtx = [[self.getElement(x, y) for y in range(4)] for x in range(4)]
        return sum(mtx, []) if flat else mtx

    def transpose(self):
        """Compute and return the transpose of this instance.

        Returns:
            Matrix: The transposed matrix.
        """
        return encode(super(Matrix, self).transpose())

    def inverse(self):
        """Compute and return the inverse of this instance.

        Returns:
            Matrix: The inverted matrix.
        """
        return encode(super(Matrix, self).inverse())

    def adjoint(self):
        """Compute and return the adjoint of this instance.

        Returns:
            Matrix: The adjoint of this matrix.
        """
        return encode(super(Matrix, self).adjoint())

    def homogenize(self):
        """Compute and return a homogenized version of this instance.

        Returns:
            Matrix: The homogenized matrix.
        """
        return encode(super(Matrix, self).homogenize())


class EulerRotation(OpenMaya.MEulerRotation):
    # pylint: disable=invalid-name
    """Euler Rotation Math.

    This class provides methods for working with euler angle rotations.
    Euler angles are described by rotations in radians around the
    x, y, and z axes, and the order in which those rotations occur.
    """
    # constructor
    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], Plug):
            super(EulerRotation, self).__init__(args[0].read())
        else:
            super(EulerRotation, self).__init__(*args, **kwargs)

    # public
    def decode(self):
        """Decode the euler rotation into a tuple."""
        return tuple(self)

    def alternateSolution(self):
        """Returns an alternate solution to this rotation.

        The resulting rotation will be bound between +/- PI,
        and the rotation order will remain unchanged.

        Returns:
            EulerRotation: An alternate solution to this rotation.
        """
        return encode(super(EulerRotation, self).alternateSolution())

    def asMatrix(self):
        """Returns the rotation as an equivalent matrix."""
        return encode(super(EulerRotation, self).asMatrix())

    def asQuaternion(self):
        """Returns the rotation as an equivalent quaternion."""
        return encode(super(EulerRotation, self).asQuaternion())

    def asVector(self):
        """Returns the X, Y and Z rotations as a vector."""
        return encode(super(EulerRotation, self).asVector())

    def bound(self):
        """Returns the result of bounding this rotation to be within +/- PI.

        Bounding a rotation to be within +/- PI is defined to be the result of
        offsetting the rotation by +/- 2nPI (term by term) such that the offset
        is within +/- PI.

        Returns:
            EulerRotation: The euler rotation that results from bounding self.
        """
        return encode(super(EulerRotation, self).bound())

    def boundIt(self, *args, **kwargs):
        """In-place bounding of each rotation component to lie wthin +/- PI."""
        return encode(super(EulerRotation, self).boundIt(*args, **kwargs))

    def closestCut(self, target):
        """Returns the closest cut of this rotation to "dst"."""
        return encode(super(EulerRotation, self).closestCut(target))

    def closestSolution(self, target):
        """Returns the equivalent rotation which comes closest to a target."""
        return encode(super(EulerRotation, self).closestSolution(target))

    def decompose(self, matrix, order):
        """Decompose a rotation matrix into the desired euler angles.

        Arguments:
            matrix (Matrix): The matrix that will be decomposed.
            order (int): The rotation order.

        Returns:
            EulerRotation: The euler rotation that has been decomposed.
        """
        return encode(super(EulerRotation, self).decompose(matrix, order))

    def inverse(self):
        """Returns the inverse of this euler rotation."""
        return encode(super(EulerRotation, self).inverse())

    def reorder(self, order):
        """Returns the reordered euler rotation."""
        return encode(super(EulerRotation, self).reorder(order))


class Quaternion(OpenMaya.MQuaternion):
    """Maya quaternion."""

    # constructor
    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], Plug):
            super(Quaternion, self).__init__(args[0].read())
        else:
            super(Quaternion, self).__init__(*args, **kwargs)


class TransformationMatrix(OpenMaya.MTransformationMatrix):
    # pylint: disable=invalid-name
    """Allows the manipulation of the individual transformation components."""

    # constructor
    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], Plug):
            super(TransformationMatrix, self).__init__(args[0].read())
        else:
            super(TransformationMatrix, self).__init__(*args, **kwargs)

    # public
    def asMatrix(self):
        """Returns the four by four matrix that describes this transformation.

        Returns:
            Matrix: The matrix.
        """
        return encode(super(TransformationMatrix, self).asMatrix())

    def asMatrixInverse(self):
        """Returns the inverse of the matrix representing the transformation.

        Returns:
            Matrix: The matrix.
        """
        return encode(super(TransformationMatrix, self).asMatrixInverse())

    def asRotateMatrix(self):
        """Returns rotate space matrix

        Returns:
            Matrix: The matrix.
        """
        return encode(super(TransformationMatrix, self).asRotateMatrix())

    def asScaleMatrix(self):
        """Returns scale  space matrix

        Returns:
            Matrix: The matrix.
        """
        return Matrix(super(TransformationMatrix, self).asScaleMatrix())

    def rotatePivot(self, space=Space.WORLD):
        """Returns the pivot around which the rotation is applied.

        Arguments:
            space (int): Space in which to get the pivot.

        Returns:
            Point: Rotation pivot point.
        """
        return Point(super(TransformationMatrix, self).rotatePivot(space))

    def rotatePivotTranslation(self, space=Space.WORLD):
        """Returns the rotation pivot translation.

        This is the translation that is used to compensate for
        the movement of the rotation pivot.

        Arguments:
            space (int): Space in which to get the pivot.

        Returns:
            Point: Rotation pivot point.
        """
        return encode(
            super(TransformationMatrix, self).rotatePivotTranslation(space)
        )

    def translation(self, space=Space.WORLD):
        """The translation component of the translation.

        Arguments:
            space (int): Space in which to perform the translation.

        Returns:
            Vector: Translation vector in centimeters.
        """
        return encode(super(TransformationMatrix, self).translation(space))

    def rotation(self, quaternion=False):
        """Get the rotation component of the transformation matrix in radians.

        Arguments:
            quaternion (bool): Return a quaternion.

        Returns:
            EulerRotation: Rotation in radian.
        """
        return encode(super(TransformationMatrix, self).rotation(quaternion))

    def scale(self, space=Space.WORLD):
        # pylint: disable=useless-super-delegation
        """Get the scale component of the transformation matrix.

        Arguments:
            space (int): Space in which to perform the translation.

        Returns:
            list: A list containing the transformation's scale components.
        """
        return super(TransformationMatrix, self).scale(space)


class BoundingBox(OpenMaya.MBoundingBox):
    """Bounding box type."""


class Color(OpenMaya.MColor):
    """Color type."""

    # constructor
    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], Plug):
            super(Color, self).__init__(args[0].read())
        else:
            super(Color, self).__init__(*args, **kwargs)


# Privates
@contextlib.contextmanager
def _restore(instance):
    """Create a restore point for the instance.

    The instance can be modified within the with statement and will
    be restored at the end of the block.

    Examples:
        >>> class Foo(object):
        ...     pass
        >>> foo = Foo()
        >>> foo.temp = 1
        >>> with _restore(foo):
        ...     foo.temp = 2
        >>> foo.temp
        1
    """
    restore_point = copy.deepcopy(instance.__dict__)
    yield
    instance.__dict__ = restore_point


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
