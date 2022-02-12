"""Provide utilities related to serialization."""
import json
import logging
import re

import yaml

LOG = logging.getLogger(__name__)

__all__ = ["json_dump"]


def json_dump(path, obj, clean=False, **kwargs):
    """Serialize a python object into a JSON file.

    Tip:
        When a dictionary that contains a list of numbers is serialized, JSON
        formats it like the following example::

            {
                "my_list": [
                    1,
                    2,
                    3,
                ]
            }

        That is not really readable. The ``clean`` parameter allows to reformat
        this to an inline list::

            {
                "my_list": [1, 2, 3]
            }

    Arguments:
        path (str): The path where the serialized object needs to be stored on
            the disk.
        obj (any): The python object to serialize.
        clean (bool, optional): Clean the list of numbers.
        **kwargs: The keyword arguments to pass to :func:`json.dumps`.
    """
    kwargs.setdefault("indent", 4)

    obj_string = json.dumps(obj, **kwargs)
    if clean:
        obj_string = re.sub(r"\n\s+(\]|\-?\d)", r"\1", obj_string)

    with open(path, "w") as stream:
        stream.write(obj_string)


class YamlDumper(yaml.Dumper):
    """Custom YAML dumper."""

    def __init__(self, *args, **kwargs):
        super(YamlDumper, self).__init__(*args, **kwargs)
        self.add_representer(str, self.string_representer)

    @staticmethod
    def string_representer(dumper, data):
        """Represent a string using a different scalar style."""
        kwargs = {}
        if "\n" in data:
            kwargs["style"] = "|"
        elif not data:
            kwargs["style"] = '"'
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, **kwargs)
