"""Provide utilities related to names."""
import logging

from maya import cmds

__all__ = ["find_conflicts", "generate_unique"]

LOG = logging.getLogger(__name__)


def find_conflicts(sets=False):
    """Find the nodes with a name that appear more than once in the scene.

    The ``sets`` parameter will generate a set that contains nodes
    with name conflicts.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> _ = cmds.createNode("transform", name="a")
        >>> _ = cmds.createNode("transform", name="a", parent="a")
        >>> find_conflicts(sets=True)
        ['|a', '|a|a']
        >>> cmds.objExists("CONFLICTS_NODES")
        True
        >>> _ = cmds.rename("|a|a", "b")
        >>> find_conflicts(sets=True)
        []
        >>> cmds.objExists("CONFLICTS_NODES")
        False

    Arguments:
        sets (bool): Create a set that will contain all nodes with a conflict.

    Returns:
        list: The conflicts node name.
    """
    nodes = [x for x in cmds.ls() if "|" in x]
    if sets:
        name = "CONFLICTS_NODES"
        if cmds.objExists(name):
            cmds.delete(name)
        if nodes:
            cmds.sets(nodes, name=name)
        else:
            LOG.info("No conflicts found! :)")
    return nodes


def generate_unique(name):
    """Generate a name that is guaranteed to be unique to avoid conflicts.

    If the base of the name contains at least one ``#`` character, it will be
    replaced by an index. The length of the index is determined by the number
    of ``#`` characters.

    Warning:
        If the name contains more than one `block` of `#``
        (e.g. ``base_###_name_####_ext``), this function will raise an error.

    It's also possible to use a wildcard (``*``) for search name. It can be
    particularly useful for finding the prefix of an entire hierarchy.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> for _ in range(3):
        ...     name = generate_unique("node")
        ...     cmds.createNode("transform", name=name)
        'node'
        'node1'
        'node2'
        >>> for _ in range(3):
        ...     name = generate_unique("node##_srt")
        ...     cmds.createNode("transform", name=name)
        'node00_srt'
        'node01_srt'
        'node02_srt'
        >>> cmds.createNode("transform", name="setup01_srt")
        'setup01_srt'
        >>> for _ in range(3):
        ...     name = generate_unique("setup##*")
        ...     cmds.createNode("transform", name=name)
        'setup00'
        'setup02'
        'setup03'
        >>> generate_unique("node##_##_ext")
        Traceback (most recent call last):
          ...
        NameError: More than one block of '#'.

    Arguments:
        name (str): The base string from which the name will be generated.

    Returns:
        str: The unique generated name.

    Raises:
        NameError: More than one block of '#'.
    """
    count = name.count("#")
    index = 0

    if "#" * count not in name:
        raise NameError("More than one block of '#'.")

    def _build():
        i = str(index).zfill(count)
        return name.replace("#" * count, i) if count else name

    generated = _build()
    while cmds.objExists(generated):
        if not count and not index:
            name += "#"
            count = 1
        index += 1
        generated = _build()

    return generated.replace("*", "")
