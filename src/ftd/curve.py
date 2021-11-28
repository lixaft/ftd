"""Provide utilities related to curves."""
from __future__ import division

import collections
import logging

from maya import cmds

import ftd.graph
import ftd.name

__all__ = [
    "cvs_position",
    "default_knots",
    "from_transform",
    "generate_weights",
    "matrix_curve",
]

LOG = logging.getLogger(__name__)

CurveError = type("CurveError", (BaseException,), {})


def cvs_position(node, world=False):
    """Query the position of each control points of a curve.

    Examples:
        >>> from maya import cmds
        >>> node = cmds.curve(
        ...     point=[(-5, 0, 0), (0, 5, 0), (5, 0, 0)],
        ...     degree=1,
        ... )
        >>> cmds.setAttr(node + ".translateZ", -2)
        >>> cvs_position(node, world=True)
        [(-5.0, 0.0, -2.0), (0.0, 5.0, -2.0), (5.0, 0.0, -2.0)]

    Arguments:
        node (str): The curve node to query.
        world (bool): Specify on which space the coordinates will be returned.

    Returns:
        list: A two-dimensional array that contains all the positions of the
        points that compose the curve.
    """
    pos = cmds.xform(
        node + ".cv[*]",
        query=True,
        translation=True,
        worldSpace=world,
        absolute=world,
    )
    # build an array with each point position in it's own array.
    return [tuple(pos[x * 3 : x * 3 + 3]) for x, _ in enumerate(pos[::3])]


def default_knots(count, degree=3):
    """Find each knot value that can be used to generate a curve.

    Examples:
        >>> default_knots(5, 1)
        [0.0, 0.0, 0.0, 0.0, 1.0, 2.0, 2.0, 2.0, 2.0]

    Arguments:
        count (int): The number of control points in the curve.
        degree (int): The degree of the curve.

    Returns:
        list: An array that contains each knot value to generate the curve.
    """
    knots = [0 for _ in range(degree)] + list(range(count - degree + 1))
    knots += [count - degree for _ in range(degree)]
    return [float(knot) for knot in knots]


def from_transform(nodes, name="curve", degree=3, close=False, attach=False):
    """Create a curve with each point at the position of a transform node.

    If the "attachment" parameter is set to "True", each cvs of the created
    curve will be driven by the node that gave it its position.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> a = cmds.createNode("transform")
        >>> b = cmds.createNode("transform")
        >>> c = cmds.createNode("transform")
        >>> cmds.setAttr(b + ".translate", 5, 10, 0)
        >>> cmds.setAttr(c + ".translate", 10, 0, 0)
        >>> from_transform((a, b, c), degree=1)
        'curve'

    Arguments:
        nodes (list): The transformation nodes to use as position.
        name (str): The name of the curve.
        degree (int): The degree of the curve.
        close (bool): Specifies if the curve is closed or not.
        attach (bool): Constrains the position of cvs at nodes.

    Returns:
        str: The curve name.
    """
    flags = {"query": True, "translation": True, "worldSpace": True}
    point = [cmds.xform(x, **flags) for x in nodes]

    flags = {}
    if close:
        point.extend(point[:degree])
        flags["periodic"] = True
        flags["knot"] = range(len(point) + degree - 1)

    name = ftd.name.generate_unique(name)
    curve = cmds.curve(point=point, degree=degree, **flags)
    curve = cmds.rename(curve, name)
    if not attach:
        return curve

    for index, node in enumerate(nodes):
        name = node + "_decomposeMatrix"
        decompose = cmds.createNode("decomposeMatrix", name=name)
        cmds.connectAttr(node + ".worldMatrix[0]", decompose + ".inputMatrix")
        cmds.connectAttr(
            decompose + ".outputTranslate",
            "{}.cv[{}]".format(curve, index),
        )

    return curve


def generate_weights(cvs, time, degree=3, knots=None):
    """Generates the weights of each control point of a curve.

    Note:
        This function is written from `Cole O'Brien`_ post.

    Arguments:
        cvs (list): An array of items that will be used at cvs.
        time (float): The location of the curve where the weights need to be
            calculate.
        degree (int): The degree of the curve.
        knots (list): The knots to use to generate the curve. By default, use
            the :func:`default_knots` function to generate them.

    Returns:
        list: An array of tuple that contains the weights of each cv.

    Raises:
        CurveError: The specified values can't generate a valid curve.

    .. _Cole O'Brien:
        https://coleobrien.medium.com/?p=ec17f3b3741
    """
    order = degree + 1

    # ensure that all data provided is correct and can be computed.
    if len(cvs) <= degree:
        msg = "Curves of degree {} require at least {} cvs."
        msg = msg.format(degree, order)
        LOG.error(msg)
        raise CurveError(msg)

    knots = knots or default_knots(len(cvs), degree)
    if len(knots) != len(cvs) + order:
        msg = (
            "Not enough knots provided. Curves with {} cvs must have a knot "
            "vector of length {}. Received a knot vector of length {}. "
            "Total knot count must equal len(cvs) + degree + 1."
        ).format(len(cvs), len(cvs) + order, len(knots))
        LOG.error(msg)
        raise CurveError(msg)

    # remap the time parameter to match the range of the knot values
    min_knot = knots[order] - 1
    max_knot = knots[len(knots) - 1 - order] + 1
    time = time * (max_knot - min_knot) + min_knot

    # determine on which segment of the curve the time value lies
    segment = degree
    for index, knot in enumerate(knots[order : len(knots) - order]):
        if knot <= time:
            segment = index + order

    # filters out cvs not used in the segment.
    indices = list(range(len(cvs)))
    used_indices = [indices[j + segment - degree] for j in range(0, order)]

    # run the boor's algorithm
    cv_weights = [{cv: 1.0} for cv in used_indices]
    for i in range(1, order):
        for j in range(degree, i - 1, -1):
            left = j + segment - degree
            right = j + 1 + segment - i
            alpha = (time - knots[left]) / (knots[right] - knots[left])

            weights = {k: v * alpha for k, v in cv_weights[j].items()}
            for idx, weight in cv_weights[j - 1].items():
                value = weight * (1 - alpha)
                if idx in weights:
                    weights[idx] += value
                else:
                    weights[idx] = value

            cv_weights[j] = weights

    # create the name tuple that will be used for the return values
    Weight = collections.namedtuple("Weight", field_names=("item", "weight"))

    return [Weight(cvs[i], j) for i, j in cv_weights[degree].items()]


def matrix_curve(drivers, drivens, parameters=None, degree=3):
    """Use the :func:`generate_weights` to generate a curve with maths.

    Arguments:
        drivers (list): The node to use as cvs for generating the curve.
        drivens (list): The node that will be attached to the curve.
        parameters (list): The time value for each drivens
        degree (int): The degree of the curve to generate.
    """
    if parameters is None:
        parameters = [x / (len(drivens) - 1) for x, _ in enumerate(drivens)]

    for time, driven in zip(parameters, drivens):
        add = cmds.createNode("wtAddMatrix")

        curve_data = generate_weights(drivers, time, degree=degree)
        for index, (obj, weight) in enumerate(curve_data):
            cmds.setAttr("{}.wtMatrix[{}].weightIn".format(add, index), weight)
            cmds.connectAttr(
                obj if "." in obj else obj + ".worldMatrix[0]",
                "{}.wtMatrix[{}].matrixIn".format(add, index),
            )

        ftd.graph.matrix_to_srt(add + ".matrixSum", driven)
