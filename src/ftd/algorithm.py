"""Provide mathematical algorithms."""
from __future__ import division

import logging

from maya.api import OpenMaya

LOG = logging.getLogger(__name__)

__all__ = ["barycentric_coordinates"]


def barycentric_coordinates(a, b, c, point):
    # pylint: disable=invalid-name
    """Generate the barycentric coordinates of the given points.

    The barycentric coordinates describe the position of a point contained
    in a triangle by a series of weights corresponding to each point of the
    triangle.

    For a point :math:`P` in a triangle :math:`ABC`, the barycentric
    coordinates of point :math:`P` are represented by the formula:

    .. math::
        P = w_aA + w_bB + w_cC

    Note:
        The sum of the three weights is equal to one:

        .. math::
            1 = w_a + w_b + w_c

    Examples:
        >>> coord = barycentric_coordinates(
        ...     a=(10, 0, 0),
        ...     b=(0, 0, 0),
        ...     c=(0, 0, 10),
        ...     point=(2, 0, 2),
        ... )
        >>> coord
        (0.2, 0.6, 0.2)
        >>> sum(coord)
        1.0

    Arguments:
        a (tuple): The first point of the triangle.
        b (tuple): The second point of the triangle.
        c (tuple): The third point of the triangle.
        point (tuple): The point on which generate the coordinates.

    Returns:
        tuple: The generated coordinates.
    """
    a, b, c, p = map(OpenMaya.MPoint, (a, b, c, point))

    global_area = ((b - a) ^ (c - a)).length()
    coordinates = (
        ((b - p) ^ (c - p)).length() / global_area,
        ((c - p) ^ (a - p)).length() / global_area,
        ((a - p) ^ (b - p)).length() / global_area,
    )
    return coordinates
