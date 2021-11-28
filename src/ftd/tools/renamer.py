"""A tool that speeds up and simplifies the renaming of nodes."""
import logging
import re

from maya import cmds
from maya.api import OpenMaya

import ftd.interaction

__all__ = ["Core"]

LOG = logging.getLogger(__name__)


class Core(object):
    """Main class for renaming nodes."""

    SELECTED = "selected"
    """str: Affects only passed nodes."""
    HIERARCHY = "hierarchy"
    """str: Affects the passed nodes and their descendants."""

    def __init__(self, mode=SELECTED):
        self._mode = None
        self._nodes = []
        self._sides = {"l": "r", "lf": "rt", "left": "right"}
        self._types = {
            "joint": "jnt",
            "mesh": "msh",
            "locator": "loc",
            "nurbsCurve": "ctrl",
            "transform": "grp",
        }

        self.mode = mode

    # Read write properties
    @property
    def mode(self):
        """str: The current mode of the renamer."""
        return self._mode

    @mode.setter
    def mode(self, value):
        value = value.lower()
        if value not in (self.SELECTED, self.HIERARCHY):
            raise ValueError("Invalid mode for the renamer.")
        self._mode = value

    @property
    def nodes(self):
        """list: The nodes to rename."""
        return list(map(self._decode, self._nodes))

    @nodes.setter
    def nodes(self, value):
        self._nodes = list(map(self._encode, value))

    # Public methods ---
    @ftd.interaction.undo
    def hash(self, name, start=0):
        """Rename the nodes by replacing the hash characters by a unique index.

        If no hash character has found, the index will be placed at the
        end of the new name. The index length is determined by the number
        of hash characters.

        Examples:
            >>> from maya import cmds
            >>> _ = cmds.file(new=True, force=True)
            >>> a = cmds.createNode("transform")
            >>> b = cmds.createNode("transform")
            >>> renamer = Core()
            >>> renamer.nodes = [a, b]
            >>> renamer.hash("node##_grp")
            >>> renamer.nodes
            ['|node00_grp', '|node01_grp']

        Arguments:
            name (str): The new name of the nodes.
            start (int): The first index to use.
        """
        length = name.count("#")
        if not length:
            name = "{}#".format(name)
            length = 1

        for index, node in enumerate(self._iter_nodes(), start=start):
            new = name.replace("#" * length, str(index).zfill(length))
            self._rename(node, new)

    @ftd.interaction.undo
    def search_replace(self, search, replace):
        """Replace all occurrences of a substring with another substring.

        The old substring can be searched using `regular expressions`_.

        Examples:
            >>> from maya import cmds
            >>> _ = cmds.file(new=True, force=True)
            >>> node = cmds.createNode("transform", name="node_old_grp")
            >>> renamer = Core()
            >>> renamer.nodes = [node]
            >>> renamer.search_replace("old", "new")
            >>> renamer.nodes
            ['|node_new_grp']

        Arguments:
            search (str): Old substring you want to replace.
            replace (str): New substring which will replace the old one.

        .. _regular expressions:
            https://www.programiz.com/python-programming/regex
        """
        regex = re.compile(search)
        for node in self._iter_nodes():
            self._rename(node, regex.sub(replace, node.name()))

    @ftd.interaction.undo
    def tokens(self, index, add=None, replace=None, remove=False):
        """Manipulates the name after separating it at each underscore.

        Separate the name using ``.split("_")`` and manipulates the
        resulting list by adding, removing or replacing tokens.
        The list will be reassembled using ``"_".joint()``.

        Examples:
            >>> from maya import cmds
            >>> _ = cmds.file(new=True, force=True)
            >>> node = cmds.createNode("transform", name="prefix_node_suffix")
            >>> renamer = Core()
            >>> renamer.nodes = [node]
            >>> renamer.tokens(0, replace="my")
            >>> renamer.nodes
            ['|my_node_suffix']
            >>> renamer.tokens(-1, remove=True)
            >>> renamer.nodes
            ['|my_node']
            >>> renamer.tokens(-1, add="grp")
            >>> renamer.nodes
            ['|my_node_grp']

        Arugments:
            index (int): The index where the operation need to be.
            add (str): Add the token to the specified index.
            replace (str): Replace the token at the specified index.
            remove (bool): Remove the token at the specified index.
        """

        for node in self._iter_nodes():
            tokens = node.name().split("_")

            if add:
                index = (len(tokens) - abs(index) + 1) if index < 0 else index
                tokens.insert(index, add)
            if replace:
                tokens[index] = replace
            if remove:
                tokens.pop(index)

            self._rename(node, "_".join(tokens))

    @ftd.interaction.undo
    def switch_case(self):
        """Switch the name case between lower and upper.

        Examples:
            >>> from maya import cmds
            >>> _ = cmds.file(new=True, force=True)
            >>> node = cmds.createNode("transform", name="abc")
            >>> renamer = Core()
            >>> renamer.nodes = [node]
            >>> renamer.switch_case()
            >>> renamer.nodes
            ['|ABC']
            >>> renamer.switch_case()
            >>> renamer.nodes
            ['|abc']
        """
        for node in self._iter_nodes():
            name = node.name()
            if name.isupper():
                new = name.lower()
            else:
                new = name.upper()
            self._rename(node, new)

    @ftd.interaction.undo
    def switch_side(self):
        """Switch the node side.

        Examples:
            >>> from maya import cmds
            >>> _ = cmds.file(new=True, force=True)
            >>> node = cmds.createNode("transform", name="L_node")
            >>> renamer = Core()
            >>> renamer.nodes = [node]
            >>> renamer.switch_side()
            >>> renamer.nodes
            ['|R_node']
        """
        sides = {}
        for key, value in self._sides.items():
            for case in ("lower", "upper", "title"):
                key_ = getattr(key, case)()
                value_ = getattr(value, case)()
                sides[key_] = value_
                sides[value_] = key_

        for node in self._iter_nodes():
            tokens = node.name().split("_")
            for old, new in sides.items():
                if tokens[0] == old:
                    tokens[0] = new
                    break
            self._rename(node, "_".join(tokens))

    @ftd.interaction.undo
    def add_type(self, overrided=None):
        """Add the type of the node as suffix.

        The type added can be overridden if the type of the node is in the
        specified dictinary at "overrided" argument. The defaults overrided
        types is :obj:`types`.

        Examples:
            >>> from maya import cmds
            >>> _ = cmds.file(new=True, force=True)
            >>> node = cmds.createNode("addDoubleLinear", name="node")
            >>> renamer = Core()
            >>> renamer.nodes = [node]
            >>> renamer.add_type()
            >>> renamer.nodes
            ['node_addDoubleLinear']
            >>> node = cmds.createNode("transform", name="node")
            >>> renamer.nodes = [node]
            >>> renamer.add_type()
            >>> renamer.nodes
            ['|node_grp']
        """
        types = self._types.copy()
        types.update(overrided or {})

        for node in self._iter_nodes():
            shapes = cmds.listRelatives(self._decode(node), shapes=True)
            if shapes:
                node_type = cmds.nodeType(shapes[0])
            else:
                node_type = node.typeName

            suffix = types.get(node_type, node_type)
            if not node.name().endswith(suffix):
                self._rename(node, "{}_{}".format(node.name(), suffix))

    # Private methods ---
    @staticmethod
    def _encode(node):
        """Encode a string to OpenMaya."""
        if not isinstance(node, OpenMaya.MObject):
            sel = OpenMaya.MSelectionList()
            sel.add(node)
            node = sel.getDependNode(0)
        if node.hasFn(OpenMaya.MFn.kDagNode):
            return OpenMaya.MFnDagNode(node)
        return OpenMaya.MFnDependencyNode(node)

    @staticmethod
    def _decode(node):
        """Decode an OpenMaya node into a string."""
        if isinstance(node, OpenMaya.MFnDagNode):
            return node.fullPathName()
        return node.name()

    @staticmethod
    def _validate(mobject):
        """Make sure that a MObject exists and does not make maya unstable."""
        handle = OpenMaya.MObjectHandle()
        handle.assign(mobject)
        return handle.isValid()

    def _iter_nodes(self):
        """Iter over the nodes to rename."""
        for node in self._nodes:

            # add the current node after checking it
            if self._validate(node.object()):
                yield node

            # continue the iteration if renaming the descendants
            # is not requested or impossible
            if not node.object().hasFn(OpenMaya.MFn.kDagNode):
                continue
            if self._mode != self.HIERARCHY:
                continue

            # initialize the dag iterator
            mit = OpenMaya.MItDag()
            mit.reset(node.object())
            # skip self
            mit.next()

            while not mit.isDone():
                child = mit.currentItem()
                if not child.hasFn(OpenMaya.MFn.kShape):
                    if self._validate(child):
                        yield self._encode(child)
                mit.next()

    def _rename(self, node, name):
        """Rename a node and its shapes."""
        name = cmds.rename(self._decode(node), name.replace(" ", "_"))
        for i, shape in enumerate(cmds.listRelatives(name, shapes=True) or []):
            cmds.rename(shape, "{}Shape{}".format(name, i if i else ""))
