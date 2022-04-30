"""Provide utilities related to names."""
import logging
import re

from maya import cmds

__all__ = ["find_conflicts", "unique", "nice"]

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
        >>> sorted(cmds.sets("CONFLICTS_NODES", query=True))
        ['|a', '|a|a']
        >>> _ = cmds.rename("|a|a", "b")
        >>> find_conflicts()
        []

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


def unique(name):
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
        ...     name = unique("node")
        ...     cmds.createNode("transform", name=name)
        'node'
        'node1'
        'node2'
        >>> for _ in range(3):
        ...     name = unique("node##_srt")
        ...     cmds.createNode("transform", name=name)
        'node00_srt'
        'node01_srt'
        'node02_srt'
        >>> cmds.createNode("transform", name="setup01_srt")
        'setup01_srt'
        >>> for _ in range(3):
        ...     name = unique("setup##*")
        ...     cmds.createNode("transform", name=name)
        'setup00'
        'setup02'
        'setup03'
        >>> unique("node##_##_ext")
        Traceback (most recent call last):
          ...
        NameError:

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


def nice(name):
    """Generate a nice name based on the given string.

    Examples:
        >>> names = [
        ...     "simple_command",
        ...     "simpleCommand",
        ...     "SimpleCommand",
        ...     "Simple command",
        ... ]
        >>> for name in names:
        ...     nice(name)
        'Simple Command'
        'Simple Command'
        'Simple Command'
        'Simple Command'

    Arguments:
        name (str): The string from which generate the nice name.

    Returns:
        str: The generated nice name.
    """
    # The regular expression will match all upper case characters except the
    # one that starts the string and insert a space before it.
    return re.sub(r"(?<!^)([A-Z])", r" \1", name).replace("_", " ").title()
