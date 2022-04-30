"""Provide utilities related to controls."""
import copy
import logging
import os

import yaml

from maya import cmds

import ftd.color
import ftd.curve

__all__ = ["SHAPES", "SIDES", "create", "replace", "mirror"]

LOG = logging.getLogger(__name__)

SHAPES = {}
"""dict: The available controls.

:meta hide-value:
"""

_PATH = os.path.join(os.path.dirname(__file__), "resources", "controls.yaml")
with open(_PATH, "r") as _stream:
    SHAPES.update(yaml.load(_stream, Loader=yaml.FullLoader))
del _PATH, _stream

SIDES = {"L": "R", "l": "l"}
"""The know sides."""


def create(shape, name=None, size=1, normal="+y", color="yellow"):
    """Create a new control.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> create("global")
        'global_ctrl'

    Arguments:
        shape (str): The shape type of the control.
        name (str): The name of the control.
        size (float): The size of the control shape.
        normal (str): The normal axis of the control shape.
            The value can be ``"x"``, ``"y"`` or ``"z"``.
        color (str): The color of the control.
            See :func:`ftd.color.name` for details.

    Returns:
        str: The name of the created control.
    """
    # Find the data that corresponds to the type of control
    data = copy.deepcopy(SHAPES.get(shape, {}))
    if not data:
        msg = "The specified type (%s) does not correspond to any file."
        LOG.error(msg, shape)
        return None

    # Ensure that the data is valid and that the curve can be correctly create
    if data.get("periodic"):
        # Ensure that the curve have the same points at the bbeginning and end
        degree = data["degree"]
        if data["point"][:degree] != data["point"][-degree:]:
            data["point"] += data["point"][:degree]
        # Generate the default values for the knots
        data.setdefault("knot", range(len(data["point"]) + degree - 1))

    # Edit the points of the shape
    if not getattr(size, "__iter__", False):
        size = [size] * 3
    if len(normal) == 2:
        sign, normal = normal[:]
        if sign == "-":
            size["xyz".index(normal)] *= -1
    remap = {"x": {0: 1, 1: 0}, "z": {1: 2, 2: 1}}.get(normal, {})
    data["point"] = _edit_points(data["point"], remap, size)

    # Create the control in maya
    control = cmds.curve(**data)
    if not name:
        name = ftd.name.unique(shape + "_ctrl")
    control = cmds.rename(control, name)
    ftd.color.name(control, color)

    return control


def replace(old, new, absolute=False, mirror_axis=None):
    """Replace the shape of a control.

    Arguments:
        old (str): The shape that will be replaced.
        new (str): The shape that the old one will be replaced by.
        absolute (bool): Takes into consideration the position
            of the transformer or not.
        mirror_axis (str): If specified, mirror the shape on the given axis.
            The value can be ``"x"``, ``"y"`` or ``"z"``.
    """
    # Populate the flags of the curve command with the new shape data
    flags = {}
    flags["point"] = ftd.curve.cvs_position(new, world=absolute)
    flags["degree"] = cmds.getAttr(new + ".degree")
    if cmds.getAttr(new + ".form") == 2:
        flags["periodic"] = 2
        flags["point"].extend(flags["point"][: flags["degree"]])
    flags["knot"] = range(len(flags["point"]) + flags["degree"] - 1)

    if mirror_axis:
        multiplier = [1] * 3
        multiplier["xyz".index(mirror_axis)] *= -1
        flags["point"] = _edit_points(flags["point"], multiplier=multiplier)

    # Maya doesn't seem to like having a periodic curve as a old control in
    # the command...  So just make sure it's not periodic before replacing it.
    if cmds.getAttr(old + ".form"):
        cmds.closeCurve(old, replaceOriginal=True, constructionHistory=False)

    # Replace the shape of the curve
    cmds.curve(old, replace=True, worldSpace=absolute, **flags)


def mirror(node, axis="x", rules=None):
    """Replace the control shape of the opposite side.

    The control on the opposite side is found by the value of
    its prefix defined in the side rules.
    The default values for the side rules are::

        {
            "L_": "R_",
            "l_": "r_",
        }

    Arguments:
        node (str): The control whose opposite one must be replaced.
        axis (str): The axis on which the control will be mirrored.
            The value can be ``"x"``, ``"y"`` or ``"z"``.
        rules (dict): Overrides the default mapping rules.
    """
    if rules is None:
        rules = SIDES.copy()
    rules.update({v: k for k, v in rules.items()})

    # Find the opposite control
    tokens = node.split("_")
    if tokens[0] not in rules:
        LOG.debug("The %s control doesn't correspond to any rule.", node)
        return

    tokens[0] = rules[tokens[0]]
    opposite = "_".join(tokens)
    if not cmds.objExists(opposite):
        LOG.debug("The %s control doesn't have an opposite.", node)
        return

    # Replace the shape of the curve
    replace(opposite, node, absolute=True, mirror_axis=axis)


def _edit_points(points, remap=None, multiplier=None):
    """Edit the points data.

    Examples:

        Replace the indices of each points values:

        >>> points = [[1, 2, 3], [4, 5, 6]]
        >>> _edit_points(points, remap={0: 1, 1: 0})
        [[2, 1, 3], [5, 4, 6]]

        Multiply the values of each point:

        >>> points = [[1, 1, 1], [2, 2, 2]]
        >>> _edit_points(points, multiplier=[-1, 1, 2])
        [[-1, 1, 2], [-2, 2, 4]]

    Arguments:
        points (list): The list of points to edit.
        remap (dict): The ``{old: new}`` index of each points.
        multiplier (list): The multiplier value of each points.

    Returns:
        list: The edited list of points.
    """
    edited_points = []
    for point in points:
        edited_point = list(point)

        if remap:
            for key, value in remap.items():
                edited_point[value] = point[key]

        if multiplier:
            edited_point = [x * y for x, y in zip(edited_point, multiplier)]

        edited_points.append(edited_point)

    return edited_points


def setup(name, shape="circle", parent=None, **kwargs):
    """Create a scalable control."""
    base = "_".join(name.split("_")[:-1])

    # Create the transform nodes.
    ctrl = create(shape, name, **kwargs)
    offset = cmds.createNode("transform", name=base + "_offset")
    scaled = cmds.createNode("transform", name=base + "_scaled")
    revert = cmds.createNode("transform", name=base + "_output")

    # Parent them into the outliner.
    cmds.parent(scaled, offset)
    cmds.parent(ctrl, scaled)
    cmds.parent(revert, ctrl)
    if parent is not None:
        cmds.parent(offset, parent)

    # Create the origShape.
    shape = cmds.listRelatives(ctrl, shapes=True)[0]
    orig = cmds.deformableShape(shape, createOriginalGeometry=True)[0]

    name = base + "_transformGeometry"
    transform = cmds.createNode("transformGeometry", name=name)
    cmds.connectAttr(scaled + ".inverseMatrix", transform + ".transform")
    cmds.connectAttr(orig, transform + ".inputGeometry")
    cmds.connectAttr(
        transform + ".outputGeometry",
        shape + ".create",
        force=True,
    )

    # Decompose matrix into SRT transform.
    name = base + "_scaled_decomposeMatrix"
    decompose = cmds.createNode("decomposeMatrix", name=name)
    cmds.connectAttr(scaled + ".inverseMatrix", decompose + ".inputMatrix")
    for attribute in (x + y for x in "srt" for y in "xyz"):
        cmds.connectAttr(
            "{}.o{}".format(decompose, attribute),
            "{}.{}".format(revert, attribute),
        )

    return ctrl
