from functools import singledispatch
from pathlib import Path
from typing import Iterable, Union

import yaml

from runtool.datatypes import DotDict, Algorithm
from runtool.infer_types import infer_types
from runtool.recurse_config import Versions
from runtool.transformer import apply_transformations


def generate_versions(data: Iterable[dict]) -> dict:
    """
    Converts an Iterable collection of dictionaries to a single dictionary.
    If two dictionaries have the same values, these values are stored in
    a `runtool.datatypes.Versions` object.

    example:

    >>> generate_versions(
    ...     [
    ...         {"a":1},
    ...         {"a":2,"b":3},
    ...     ]
    ... )
    {'a': Versions([1, 2]), 'b': 3}


    >>> generate_versions([{"a": 1}])
    {'a': 1}

    >>> generate_versions([{"a": 1}, {"a": 2}])
    {'a': Versions([1, 2])}

    >>> generate_versions([{"a": 1}, {"a": 2}, {"a": 3}])
    {'a': Versions([1, 2, 3])}
    """

    result = {}
    for dct in data:
        for key, value in dct.items():
            if key not in result:
                # first time a value occurs, store it
                result[key] = value
            elif (
                not isinstance(result[key], Versions) and result[key] != value
            ):
                # second time a value occurs for the same key
                # store these values into a Versions object
                result[key] = Versions([result[key], value])
            elif value not in result[key]:
                # if a key occurs with unique values 3+ times append
                # the value to the previously created Versions object
                result[key].append(value)
    return result


def load_config(path: Union[str, Path]) -> DotDict:
    """
    Loads a yaml file from the provided path and calls converts it
    to a dictionary and then calls `transform_config` on the data.
    """
    path = Path(path)
    with path.open() as config:
        return transform_config(yaml.safe_load(config))


def transform_config(config: dict) -> DotDict:
    """
    This function applies a series of transformations to a runtool config
    before converting it into a DotDict. The config is transformed through
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
