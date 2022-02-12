"""Populate the color configuration."""
import os
import re
import sys

import webcolors
import yaml


def clean_list(match):
    """Convert yaml list to one-line."""
    data = match.group(0).split("\n")
    data = [x.replace("-", "").strip() for x in data if x]
    return " {}\n".format(str(data).replace("'", ""))


def main():
    """Find a populate the configuration file."""
    # Find the yaml config file path.
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config = os.path.join(base, "src", "ftd", "configs", "colors.yaml")

    # Find the color data.
    colors = {}
    for color in webcolors.CSS3_NAMES_TO_HEX:
        colors[color] = {
            "hex": webcolors.name_to_hex(color),
            "rgb": list(webcolors.name_to_rgb(color)),
            "percent": list(webcolors.name_to_rgb_percent(color)),
        }

    # Write the color data to the config file.
    raw = yaml.dump(colors)
    for search, replace in {"'": '"', "%": ""}.items():
        raw = raw.replace(search, replace)
    raw = re.sub(r"\n(?: *(?:- .*\n))+", clean_list, raw)
    with open(config, "w") as stream:
        stream.write(raw)

    return 0


if __name__ == "__main__":
    sys.exit(main())
