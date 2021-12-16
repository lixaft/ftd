"""Provide utilities related to viewport."""
import logging

from maya import cmds

__all__ = ["toggle_view"]

LOG = logging.getLogger(__name__)


def toggle_view(element, panel=None):
    """Toggles the visibility of an element in the viewport.

    The function simply wraps the :func:`cmds.modelEditor` command to toggle
    the visibility of the specified element in a single line.

    See the `modelEditor`_ command in the official documentation.

    Examples:
        >>> from maya import cmds
        >>> panel = cmds.getPanel(withFocus=True)
        >>> toogle_view(element="joint")
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
