"""Provide utilities related to nodes."""
import logging
import re

from maya import cmds

LOG = logging.getLogger(__name__)

__all__ = []


def find(expression):
    """Find nodes based on regular expression"""
    regex = re.compile(expression)
    for each in cmds.ls():
        if regex.match(each):
            yield each
