"""Provide utilities related to meshes."""
import logging
import operator

from maya.api import OpenMaya

LOG = logging.getLogger(__name__)

__all__ = ["closest_vertex"]


def closest_vertex(mesh, origin):
    """Find the closest vertex to a given position.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> mesh = cmds.polyCube()[0]
        >>> closest_vertex(mesh, (0.5, 2, 0.5))
        (3, 1.5)

    Arguments:
        mesh (str): The name of the mesh on which the vertex will be searched.
        origin (tuple): The x, y and z positions of the point to use as the
            origin.

    Returns:
        tuple: The index of the closest vertex as the first index and its
        distance from the origin as the second index.
    """
    sel = OpenMaya.MSelectionList()
    sel.add(mesh)

    space = OpenMaya.MSpace.kWorld
    mfn = OpenMaya.MFnMesh(sel.getDagPath(0).extendToShape())
    point = OpenMaya.MPoint(origin)

    # first find the closest face on the mesh
    face = mfn.getClosestPoint(point, space=space)[1]

    # then iterates through each vertex of the face to compare their distance
    # with the origin point.
    vertices = []
    for vertex in mfn.getPolygonVertices(face):
        distance = mfn.getPoint(vertex, space=space).distanceTo(point)
        vertices.append((vertex, distance))

    # finally return the vertex with the smallest distance
    return min(vertices, key=operator.itemgetter(1))
