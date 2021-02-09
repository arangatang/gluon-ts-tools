from functools import singledispatch
from typing import Any, Union, List, Dict
from runtool.datatypes import (
    Algorithm,
    Algorithms,
    Dataset,
    Datasets,
    Versions,
)


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


@singledispatch
def convert(data: Any) -> Any:
    """
    Base case of singledispatch which converts a
    JSON-like structure to Algorithms, Datasets and Generics
    """
    return data


@convert.register
def convert_list(data: list) -> list:
    return [infer_type(item) for item in data]


@convert.register
def convert_dict(data: dict) -> dict:
    return {key: infer_type(value) for key, value in data.items()}
