"""Generate proxy geometries from skincluster weights map."""
import logging

from maya import cmds
from maya.api import OpenMaya, OpenMayaAnim

__all__ = ["generate", "ProxyGenerator"]

LOG = logging.getLogger(__name__)


def generate(mesh, method="constraint"):
    """Generate the proxy geometries of the specified mesh.

    Arguments:
        mesh (str): The name of the mesh to be generated.
        method (str): The method to use for constraining the proxy geometries

    Returns:
        ProxyGenerator: The proxy generator instance.
    """
    generator = ProxyGenerator(mesh)
    generator.create()
    try:
        generator.METHODS[method]()
    except KeyError:
        LOG.error("Invalid value for method parameter.")
    return generator


class ProxyGenerator(object):
    """Generate the proxy geometries from the skincluster weights.

    The weights of each polygon are analysed to find the influence that has
    the largest weight values on it.

    Tip:
        To get a clean cut, it is recommended to paint a specific map where
        the weights are only 0 or 1. However, it is still possible to generate
        the meshes on the normal map but the cuts may not be straight and will
        be more difficult to predict.

    Arguments:
        mesh (str): The name of the mesh to compute.

    Raises:
        TypeError: The specified node is not a mesh shape.
    """

    def __init__(self, mesh):
        self._influences = []
        self._data = {}
        self._proxies = {}

        # Find the mesh function set
        sel = OpenMaya.MSelectionList()
        sel.add(mesh)
        mobject = sel.getDependNode(0)

        if not mobject.hasFn(OpenMaya.MFn.kShape):
            dag = sel.getDagPath(0)
            dag.extendToShape()
            mobject = dag.node()

        if not mobject.hasFn(OpenMaya.MFn.kMesh):
            msg = "The node '{}' is not a mesh and cannot be computed."
            raise TypeError(msg.format(mesh))

        self._mesh = OpenMaya.MFnMesh(mobject)
        self.compute()

    # Read properties ---
    @property
    def mesh(self):
        """str: The name of the mesh attached to the generator."""
        return OpenMaya.MFnDagNode(self._mesh.parent(0)).name()

    # Public methods
    def compute(self):
        """Calculate the :attr:`mesh` to extract the information needed."""

        # Find the binded skincluster by iterating over the graph
        mit = OpenMaya.MItDependencyGraph(
            self._mesh.object(),
            filter=OpenMaya.MFn.kSkinClusterFilter,
            direction=OpenMaya.MItDependencyGraph.kUpstream,
            traversal=OpenMaya.MItDependencyGraph.kDepthFirst,
            level=OpenMaya.MItDependencyGraph.kNodeLevel,
        )
        if mit.isDone():
            raise RuntimeError("No binded skincluster found.")

        skincluster = OpenMayaAnim.MFnSkinCluster(mit.currentNode())
        influence_objects = skincluster.influenceObjects()

        # Variables that will be filled during the iteration of on the faces
        faces_per_influences = {}
        vertices_per_face = {}

        # Iterate over each face:
        # The main goal is to obtain the influence of the face that has the
        # greatest weight on the skincluster and to associate the face index
        # with the influence node.
        mit = OpenMaya.MItMeshPolygon(self._mesh.object())
        while not mit.isDone():
            vertices = mit.getVertices()

            # Store all the weights classed by influence
            values = {}
            weight_list = skincluster.findPlug("weightList", False)
            for vertex in vertices:
                weights = weight_list.elementByLogicalIndex(vertex).child(0)
                for influence, _ in enumerate(skincluster.influenceObjects()):
                    weight = weights.elementByLogicalIndex(influence)
                    values.setdefault(influence, []).append(weight.asDouble())

            # Find the greatest weight by adding the weights of each
            # influence to obtain the greatest result
            sums = [sum(values) for values in values.values()]
            greatest = sums.index(max(sums))

            # Populate the previously created variables
            faces_per_influences.setdefault(greatest, []).append(mit.index())
            vertices_per_face[mit.index()] = vertices

            # Jump to the next face
            mit.next()

        # Build the data needed to create the proxy geometries.
        self._data = {}
        for influence, faces in faces_per_influences.items():
            # Initialize the arrays required by maya to build a mesh:
            vertices = []  # the position of each vertex
            polygon_counts = []  # the number of vertices on each face
            polygon_connects = []  # the associated vertices ids of each face

            # Find all the face indices present in the proxy
            indices = {v for f in faces for v in vertices_per_face[f]}

            # The `old: new` index mapping
            mapid = {}

            for new, old in enumerate(indices):
                # Populate the vertex position
                vertices.append(self._mesh.getPoint(old))
                # Populate the vertex id mapping
                mapid[old] = new

            for face in faces:
                face_vertices = vertices_per_face[face]
                # Append the amount of vertices on the face.
                polygon_counts.append(len(face_vertices))
                # And the index of each of them.
                polygon_connects.extend([mapid[x] for x in face_vertices])

            data = (vertices, polygon_counts, polygon_connects)
            self._data[influence_objects[influence].partialPathName()] = data

    def create(self):
        """Create the proxy geometries from the computed data."""
        self._proxies.clear()

        # Find the initial shader group
        sel = OpenMaya.MSelectionList()
        sel.add("initialShadingGroup")
        shader = OpenMaya.MFnSet(sel.getDependNode(0))

        name = "proxy_grp"
        try:
            sel = OpenMaya.MSelectionList()
            sel.add(name)
            group = sel.getDependNode(0)
        except RuntimeError:
            mod = OpenMaya.MDagModifier()
            group = mod.createNode("transform")
            mod.renameNode(group, name)
            mod.doIt()

        for influence, data in self._data.items():
            transform = OpenMaya.MFnTransform()
            transform.create(group)
            transform.setName("{}_{}_PROXY_msh".format(self.mesh, influence))

            mesh = OpenMaya.MFnMesh()
            mesh.create(*data, parent=transform.object())
            mesh.setName(transform.name() + "Shape")

            shader.addMember(transform.object())
            self._proxies[influence] = transform.name()

    def constraint_maya(self):
        """Constrain the proxies to their influence using maya constraints."""
        for driver, driven in self._proxies.items():
            cmds.parentConstraint(driver, driven, maintainOffset=True)
            cmds.scaleConstraint(driver, driven, maintainOffset=True)

    def constraint_matrix(self):
        """Contraint the proxies using matrix nodes."""
        for driver, driven in self._proxies.items():
            mult = cmds.createNode("multMatrix")

            matrix = cmds.getAttr(driver + ".worldMatrix[0]")
            cmds.setAttr(mult + ".matrixIn[0]", matrix, type="matrix")
            cmds.connectAttr(driver + ".worldMatrix[0]", mult + ".matrixIn[1]")
            cmds.connectAttr(driven + ".pim[0]", mult + ".matrixIn[2]")

            decompose = cmds.createNode("decomposeMatrix")
            cmds.connectAttr(mult + ".matrixSum", decompose + ".inputMatrix")
            for attribute in (x + y for x in "srt" for y in "xyz"):
                cmds.connectAttr(
                    "{}.o{}".format(decompose, attribute),
                    "{}.{}".format(driven, attribute),
                )

    METHODS = {
        "constraint": constraint_maya,
        "matrix": constraint_matrix,
    }
