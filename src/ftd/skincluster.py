"""Provide utilities related to skinclusters."""
import logging

from maya import cmds, mel

__all__ = ["add", "bind", "find_influences", "remove", "remove_unused"]

LOG = logging.getLogger(__name__)


def add(node, influences):
    """Add influences to an existing skincluster.

    Note:
        If the specified node does not have a skincluster attached to it,
        simply log an error without doing anything else.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> msh, _ = cmds.polyCube()
        >>> a = cmds.createNode("joint", name="A")
        >>> b = cmds.createNode("joint", name="B")
        >>> _ = cmds.skinCluster(msh, a)
        >>> cmds.skinCluster(msh, query=True, influence=True)
        ['A']
        >>> add(msh, [b])
        >>> cmds.skinCluster(msh, query=True, influence=True)
        ['A', 'B']

    Arguments:
        node (str): The deformed node on which the skincluster is attached.
        influences (list): The influences nodes to add to the skincluster.
    """
    skincluster = mel.eval("findRelatedSkinCluster {}".format(node))
    if not skincluster:
        LOG.error("No skincluster found under the node '%s'.", node)
        return
    inf = set(influences) - set(find_influences(skincluster))
    cmds.skinCluster(skincluster, edit=True, addInfluence=list(inf))


def bind(node, influences, method="blend"):
    """Create and attach a skincluster to the specified node.

    If the target node already has a skincluster, add the missing influences
    to a skincluster using the use the :func:`add` function.

    The ``method`` parameter defines the algorithm used to get the position of
    each component of the deformed object. The possible values are:

    .. csv-table::
        :header: Value, Description

        ``linear``,          todo...
        ``dualQuaternion``,  todo...
        ``blend``,           todo...

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> msh, _ = cmds.polyCube(name="cube")
        >>> joints = [cmds.createNode("joint") for _ in range(3)]
        >>> bind(msh, joints)
        'cube_skinCluster'

    Arguments:
        node (str): The node on which creates the skincluster.
        influences (list, optional): The influence objects that will deform
            the skincluster.
        method (str): The binded method that will be used to deform the mesh.
    """
    skincluster = mel.eval("findRelatedSkinCluster {}".format(node))

    methods = {"linear": 0, "dualQuaternion": 1, "blend": 2}
    if method not in methods:
        LOG.error("The method '%s' is not valid.", method)
        return None

    if not skincluster:
        skincluster = cmds.skinCluster(
            node,
            influences,
            name=node + "_skinCluster",
            skinMethod=methods[method],
            toSelectedBones=True,
            removeUnusedInfluence=False,
        )[0]
    else:
        add(node, "")

    return skincluster


def find_influences(node, weighted=True, unused=True):
    """Get the associated influence objects associated to a skincluster.

    Example:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> msh, _ = cmds.polyCube()
        >>> a = cmds.createNode("joint", name="A")
        >>> b = cmds.createNode("joint", name="B")
        >>> skc = cmds.skinCluster(msh, a, b)[0]
        >>> find_influences(msh)
        ['A', 'B']

        Filter the weighted influences.

        >>> cmds.skinPercent(
        ...     skc,
        ...     msh + ".vtx[*]",
        ...     transformValue=[(a, 1), (b, 0)],
        ... )
        >>> find_influences(msh, weighted=True, unused=False)
        ['A']
        >>> find_influences(msh, weighted=False, unused=True)
        ['B']

    Arguments:
        node (str): The node on which query the influence objects.
        weighted (bool): Include the influence objects with non-zero weights.
        unused (bool): Include the influence objects with zero weights.

    Returns:
        list: An array containing the influence objects.
    """
    skc = mel.eval("findRelatedSkinCluster {}".format(node))
    all_ = cmds.skinCluster(skc, query=True, influence=True)
    if unused and weighted:
        return all_
    weighted_ = cmds.skinCluster(node, query=True, weightedInfluence=True)
    if weighted:
        return weighted_
    return list(set(all_) - set(weighted_))


def remove(node, influences):
    """Remove influences to an existing skincluster.

    Note:
        If the specified node does not have a skincluster attached to it,
        simply log an error without doing anything else.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> msh, _ = cmds.polyCube()
        >>> a = cmds.createNode("joint", name="A")
        >>> b = cmds.createNode("joint", name="B")
        >>> _ = cmds.skinCluster(msh, a, b)
        >>> cmds.skinCluster(msh, query=True, influence=True)
        ['A', 'B']
        >>> remove(msh, [b])
        >>> cmds.skinCluster(msh, query=True, influence=True)
        ['A']

    Arguments:
        node (str): The deformed node on which the skincluster is attached.
        influences (list): The influence nodes to add to the skincluster.
    """
    skincluster = mel.eval("findRelatedSkinCluster {}".format(node))
    if not skincluster:
        LOG.error("No skincluster found under the node '%s'.", node)
        return
    inf = set(influences) & set(find_influences(skincluster))
    LOG.debug(str(inf))
    cmds.skinCluster(skincluster, edit=True, removeInfluence=list(inf))


def remove_unused(node):
    """Remove the unused influences using the :func:`remove` function.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> msh, _ = cmds.polyCube()
        >>> a = cmds.createNode("joint", name="A")
        >>> b = cmds.createNode("joint", name="B")
        >>> skc = cmds.skinCluster(msh, a, b)[0]
        >>> cmds.skinPercent(
        ...     skc,
        ...     msh + ".vtx[*]",
        ...     transformValue=[(a, 1), (b, 0)],
        ... )
        >>> remove_unused(msh)
        >>> cmds.skinCluster(msh, query=True, influence=True)
        ['A']

    Arguments:
        node (str): The deformed node on which the skincluster is attached.
    """
    LOG.debug(str(find_influences(node, weighted=False, unused=True)))
    remove(node, find_influences(node, weighted=False, unused=True))
