"""Provide utilities related to viewport."""
import logging

from maya import cmds

__all__ = ["toggle_element"]

LOG = logging.getLogger(__name__)


def toggle_element(element, panel=None):
    """Toggles the visibility of an element in the viewport.

    The function simply wraps the :func:`cmds.modelEditor` command to toggle
    the visibility of the specified element in a single line.

    See the `modelEditor`_ command in the official documentation.

    Examples:
        >>> from maya import cmds
        >>> panel = cmds.getPanel(withFocus=True)
        >>> toggle_element("joint")
        >>> cmds.modelEditor(panel, query=True, joint=True)
        False

    Arguments:
        element (str): The UI element to show or hide. This should be a
            parameter of the :func:`cmds.modelEditor` command, e.g. ``joints``.
        panel (str, optional): The panel on which toggles the element.
            By default, operate on the current panel.

    .. _modelEditor:
        https://help.autodesk.com/view/MAYAUL/2022/ENU/?guid=__CommandsPython_index_html
    """
    if panel is None:
        panel = cmds.getPanel(withFocus=True)
    state = cmds.modelEditor(panel, query=True, **{element: True})
    cmds.modelEditor(panel, edit=True, **{element: not state})


def is_visible(node):
    """Check if the node is visible by querying all its ancestors.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> a = cmds.createNode("transform", name="A")
        >>> b = cmds.createNode("transform", name="B", parent=a)
        >>> cmds.setAttr(a + ".visibility", False)
        >>> cmds.getAttr(b + ".visibility")
        True
        >>> is_visible(b)
        False

    Arguments:
        node (str): The node to check.

    Returns:
        bool: True if the node is visible, False otherwise.
    """
    path = cmds.ls(node, long=True)[0]
    while "|" in path:
        path, tail = path.rsplit("|", 1)
        visible = cmds.getAttr(tail + ".visibility")
        if not visible:
            return False
    return True
