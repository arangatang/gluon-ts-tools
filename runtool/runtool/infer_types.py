from typing import Any, Union

from runtool.datatypes import Algorithm, Algorithms, Dataset, Datasets


def infer_type(node: Union[list, dict]) -> Any:
    """
    infer_type converts a list or a dict into an instance
    of one of the following classes.

    - Algorithm
    - Algorithms
    - Dataset
    - Datasets

    Example:
    >>> algorithm = {
    ...     "image": "image_name",
    ...     "instance": "ml.m5.2xlarge",
    ...     "hyperparameters": {},
    ... }
    >>> dataset = {
    ...     "path": {
    ...         "train": "some path"
    ...     },
    ...     "meta": {},
    ... }

    >>> isinstance(infer_type(algorithm), Algorithm)
    True

    >>> isinstance(infer_type([algorithm]), Algorithms)
    True

    >>> isinstance(infer_type(dataset), Dataset)
    True

    >>> isinstance(infer_type([dataset]), Datasets)
    True

    >>> isinstance(infer_type({}), dict)
    True

    """
    for class_ in (Algorithm, Algorithms, Dataset, Datasets):
        if class_.verify(node):
            return class_(node)
    return node


def infer_types(data: dict) -> dict:
    return {key: infer_type(value) for key, value in data.items()}
