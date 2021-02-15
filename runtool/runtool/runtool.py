from functools import singledispatch
from pathlib import Path
from typing import Iterable

import yaml

from runtool.datatypes import DotDict, Algorithm
from runtool.infer_types import infer_types
from runtool.recurse_config import Versions
from runtool.transformer import apply_transformations


def generate_versions(data: Iterable) -> dict:
    """
    Converts a list of dictionaries to a single dictionary.
    If two dictionaries has the same values, these values are stored in
    a `runtool.datatypes.Versions` object.

    example:

    >>> generate_versions(
    ...     [
    ...         {"a":1},
    ...         {"a":2,"b":3},
    ...     ]
    ... )
    {'a': Versions([1, 2]), 'b': 3}
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
def load_config(_):
    """
    The load_config singledispatch function loads a config.yml file into a DotDict.
    This function is overloaded such that it can load a config either from a str,
    pathlib.Path object or from a dictionary.
    """
    raise TypeError(
        "load_config takes either a dict or a path to a config.yml file."
    )


@load_config.register
def load_config_str(path: str) -> DotDict:
    """
    Converts the passed data to a pathlib.Path object and recursivelly calls load_config.
    """
    return load_config(Path(path))


@load_config.register
def load_config_path(path: Path) -> DotDict:
    """
    Loads a config file from a `pathlib.Path` and recursively calls `load_config` on the loaded data.
    """
    with path.open() as file:
        return load_config(yaml.safe_load(file))


@load_config.register
def load_config_dict(config: dict) -> DotDict:
    """
    This function applies a series of transformations to a runtool config
    before converting it into a DotDict. The config is transformed using
    the following procedure:

    First, the config will have any $ statements such as $each or $eval
    resolved using the `runtool.transformer.apply_transformations`
    function on the config.

    i.e.

    >>> transformed = apply_transformations(
    ...     {
    ...         "my_algorithm": {"image": {"$each": ["1", "2"]}, "instance":'...'},
    ...     }
    ... )
    >>> transformed == [
    ...     {'my_algorithm': {'image': '1', 'instance': '...'}},
    ...     {'my_algorithm': {'image': '2', 'instance': '...'}}
    ... ]
    True

    Thereafter, each dictionary in the list returned by `apply_transformations`
    will be converted to a suitable datatype by calling the
    `runtool.infer_type.infer_types` method.
    In the example below, `my_algorithm` is converted to a
    `runtool.datatypes.Algorithm` object:

    >>> inferred = [infer_types(item) for item in transformed]
    >>> inferred == [
    ...     {'my_algorithm': Algorithm({'image': '1', 'instance': '...'})},
    ...     {'my_algorithm': Algorithm({'image': '2', 'instance': '...'})}
    ... ]
    True

    The list of dicts which we now have is then converted into a dict
    of Versions objects via the `generate_versions` function.

    >>> as_versions = generate_versions(inferred)
    >>> as_versions == {
    ...     "my_algorithm": Versions(
    ...         [
    ...             Algorithm({"image": "1", "instance": "..."}),
    ...             Algorithm({"image": "2", "instance": "..."})
    ...         ]
    ...     )
    ... }
    True

    Finally, the dict is converted to a DotDict and returned.
    """
    return DotDict(
        generate_versions(
            infer_types(item) for item in apply_transformations(config)
        )
    )
