from functools import singledispatch
from typing import Any, Union, List, Dict
from runtool.datatypes import (
    Algorithm,
    Algorithms,
    Dataset,
    Datasets,
    Versions,
)


@singledispatch
def infer_type(node: Any) -> Any:
    """
    infer_type converts a node into one
    of the following objects if possible;
    - Algorithm
    - Dataset
    - Algorithms
    - Datasets

    structure to Algorithms, Datasets or Generics depending on the
    contents of each node.
    """
    return node


@infer_type.register
def infer_type_list(node: list) -> Union[Algorithms, Datasets, Any]:
    if Algorithms.verify(node):
        return Algorithms(node)
    elif Datasets.verify(node):
        return Datasets(node)
    else:
        return node


@infer_type.register
def infer_type_dict(node: dict) -> Union[Algorithm, Dataset, Any]:
    if Algorithm.verify(node):
        return Algorithm(node)
    elif Dataset.verify(node):
        return Dataset(node)
    else:
        return node


@singledispatch
def convert(data: Any) -> Any:
    """
    Base case of singledispatch which converts a
    JSON-like structure to Algorithms, Datasets and Generics
    """
    return data


@convert.register
def convert_list(data: list) -> List[Any]:
    return [infer_type(item) for item in data]


@convert.register
def convert_dict(data: dict) -> Dict:
    return {key: infer_type(value) for key, value in data.items()}


@convert.register
def convert_versions(data: Versions) -> Versions:
    return Versions([infer_type(item) for item in data])
