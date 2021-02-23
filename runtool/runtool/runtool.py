from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Union

import boto3
import yaml
from toolz import valmap

from runtool.datatypes import (
    Algorithm,
    Algorithms,
    Dataset,
    Datasets,
    DotDict,
    Experiment,
    Experiments,
)
from runtool.dispatcher import JobsDispatcher
from runtool.experiments_converter import generate_sagemaker_json
from runtool.recurse_config import Versions
from runtool.transformer import apply_transformations


class Client:
    def __init__(
        self, role: str, bucket: str, session: boto3.Session = boto3.Session()
    ) -> None:
        self.role = role
        self.bucket = bucket
        self.session = session
        self.dispatcher = JobsDispatcher(session)

    def run(
        self,
        experiment: Union[Experiments, Experiment],
        experiment_name: str = "default experiment name",
        runs: int = 1,
        job_name_expression: str = None,
        tags: dict = {},
    ):
        json_stream = generate_sagemaker_json(
            experiment,
            runs=runs,
            experiment_name=experiment_name,
            job_name_expression=job_name_expression,
            tags=tags,
            creation_time=datetime.utcnow().strftime("%Y-%m-%d-%H-%M-%S"),
            bucket=self.bucket,
            role=self.role,
        )
        tmp = list(json_stream)
        print(tmp)
        print(len(tmp))
        # self.dispatcher.dispatch(json_stream)
        raise NotImplementedError


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
