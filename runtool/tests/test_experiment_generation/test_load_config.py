from runtool.datatypes import (
    Algorithm,
    Algorithms,
    Dataset,
    Datasets,
    Experiment,
    Experiments,
)
from typing import Any
from runtool.runtool import transform_config

DATASET = {
    "path": {
        "train": "s3://gluonts-run-tool/gluon_ts_datasets/constant/train/data.json",
        "test": "s3://gluonts-run-tool/gluon_ts_datasets/constant/test/data.json",
    }
}

ALGORITHM = {
    "image": "012345678901.dkr.ecr.eu-west-1.amazonaws.com/gluonts/cpu:latest",
    "instance": "ml.m5.xlarge",
    "hyperparameters": {
        "prediction_length": 7,
        "freq": "D",
    },
}


def compare(source: dict, expected: Any):
    assert transform_config(source) == expected


def test_experiment_identification():
    compare(
        {"my_experiment": {"algorithm": ALGORITHM, "dataset": DATASET}},
        {"my_experiment": Experiment(ALGORITHM, DATASET)},
    )


def test_experiments_identification():
    compare(
        {"my_experiments": [{"algorithm": ALGORITHM, "dataset": DATASET}]},
        {"my_experiments": Experiments([Experiment(ALGORITHM, DATASET)])},
    )


def test_algorithm_identification():
    compare(
        {"algorithm": ALGORITHM},
        {"algorithm": Algorithm(ALGORITHM)},
    )


def test_algorithms_identification():
    compare(
        {"algo": [ALGORITHM]},
        {"algo": Algorithms([Algorithm(ALGORITHM)])},
    )


def test_dataset_identification():
    compare(
        {"ds": DATASET},
        {"ds": Dataset(DATASET)},
    )


def test_datasets_identification():
    compare(
        {"ds": [DATASET]},
        {"ds": Datasets([Dataset(DATASET)])},
    )


def test_all_in_one():
    compare(
        {
            "dataset": DATASET,
            "datasets": [DATASET],
            "algorithm": ALGORITHM,
            "algorithms": [ALGORITHM],
            "experiment": {"algorithm": ALGORITHM, "dataset": DATASET},
            "experiments": [{"algorithm": ALGORITHM, "dataset": DATASET}],
        },
        {
            "dataset": Dataset(DATASET),
            "datasets": Datasets([Dataset(DATASET)]),
            "algorithm": Algorithm(ALGORITHM),
            "algorithms": Algorithms([Algorithm(ALGORITHM)]),
            "experiment": Experiment(ALGORITHM, DATASET),
            "experiments": Experiments([Experiment(ALGORITHM, DATASET)]),
        },
    )
