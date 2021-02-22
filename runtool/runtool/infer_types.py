from typing import Any, Union

from runtool.datatypes import (
    Algorithm,
    Algorithms,
    Dataset,
    Datasets,
    Experiment,
    Experiments,
)
from toolz import valmap


def infer_type(node: Union[list, dict]) -> Any:
    """
    infer_type converts a list or a dict into an instance
    of one of the following classes.

    - Algorithm
    - Algorithms
    - Dataset
    - Datasets
    - Experiment
    - Experiments

    All these classes has a "verify" method implemented.
    The "verify" method will be called with the node as parameter
    for each class in sequence.
    If "verify" returns True, the node is converted
    to an instance of that class.

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

    >>> experiment = {"dataset": dataset, "algorithm": algorithm}
    >>> isinstance(infer_type(experiment), Experiment)
    True

    >>> isinstance(infer_type([experiment]), Experiments)
    True

    If the node matches multiple classes, the first match will be returned.
    An example of this is when a dictionary contains both a valid algorithm
    and a valid dataset. See below example.

    >>> isinstance(infer_type(dict(**algorithm, **dataset)), Algorithm)
    True

    For those cases where no class can verify the node,
    the node is returned.
    >>> isinstance(infer_type({}), dict)
    True

    >>> isinstance(infer_type([]), list)
    True

    >>> isinstance(infer_type([algorithm, dataset]), list)
    True

    """
    for class_ in (
        Algorithm,
        Algorithms,
        Dataset,
        Datasets,
        Experiment,
        Experiments,
    ):
        if class_.verify(node):
            return class_(node)
    return node


def infer_types(data: dict) -> dict:
    return valmap(infer_type, data)
