from functools import singledispatch
from pathlib import Path
from typing import Iterable, Union

import yaml

from runtool.datatypes import DotDict
from runtool.infer_types import convert, infer_type
from runtool.recurse_config import Versions
from runtool.transformer import apply_transformations


def generate_versions(data: Iterable) -> dict:
    """
    Converts a list of dictionaries to a single dictionary.
    If two dictionaries has the same values, these values are stored in
    a `runtool.datatypes.Versions` object.

    example:

    >>> generate_config(
    ...     [
    ...         {"a":1},
    ...         {"a":2,"b":3},
    ...     ]
    ... )
    {
        "a": Versions([1,2]),
        "b": 3
    }
    """
    base = {}
    for item in data:
        for key, value in item.items():
            if key not in base:
                # first time a value occurs, store it
                base[key] = value
            elif not isinstance(base[key], Versions) and base[key] != value:
                # If multiple values with the same keys exists
                # merge these into a Versions object
                base[key] = Versions([base[key], value])
            elif not value in base[key]:  # only store unique values
                base[key].append(value)
    return base


@singledispatch
def load_config(data):
    raise TypeError(
        "load_config takes either a dict or a path to a config.yml file."
    )


@load_config.register
def load_config_str(data: str):
    """
    Converts the passed data to a pathlib.Path object and recursivelly calls load_config.
    """
    return load_config(Path(data))


@load_config.register
def load_config_path(data: Path):
    """
    Loads a config file from a path and recursively calls load_config on the loaded data.
    """
    with data.open() as file:
        return load_config(yaml.safe_load(file))


@load_config.register
def load_config_dict(data: dict):
    """
    applies transformation to the passed data and infers the datatypes on the returned data.
    The datatypes are then merged into a dict with Versions object for those keys which map to
    multiple values.
    """
    return DotDict(
        generate_versions(
            convert(item) for item in apply_transformations(data)
        )
    )
