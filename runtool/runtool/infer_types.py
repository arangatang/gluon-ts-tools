from typing import Any, Union

from runtool.datatypes import Algorithm, Algorithms, Dataset, Datasets


def infer_type(node: Union[list, dict]) -> Any:
    """
    infer_type converts a list or a dict into one
    of the following objects if the node has a matching structure.

    - Algorithm
    - Dataset
    - Algorithms
    - Datasets

    If no match is found for the node, the node is returned unaltered
    """
    for class_ in (Algorithm, Algorithms, Dataset, Datasets):
        if class_.verify(node):
            return class_(node)
    return node


def infer_types(data: dict) -> dict:
    return {key: infer_type(value) for key, value in data.items()}
