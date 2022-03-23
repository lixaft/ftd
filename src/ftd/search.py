"""Common utilities to search nodes in the current scene."""
import logging
import re

from maya import cmds

LOG = logging.getLogger(__name__)

__all__ = ["regex"]


def regex(expression):
    """Find nodes based on regular expression.

    Arguments:
        expression (str): The regex that should match the node name to search.

    Yield:
        str: The name of the node that match the expression.
    """
    regex_ = re.compile(expression)
    for each in cmds.ls():
        if regex_.match(each):
            yield each
