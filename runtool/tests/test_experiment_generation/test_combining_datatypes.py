from runtool.datatypes import (
    Algorithms,
    Algorithm,
    Datasets,
    Dataset,
    Experiment,
    Experiments,
)
import pytest

ALGORITHM = Algorithm(
    {
        "image": "012345678901.dkr.ecr.eu-west-1.amazonaws.com/gluonts/cpu:latest",
        "instance": "ml.m5.xlarge",
        "hyperparameters": {
            "prediction_length": 7,
            "freq": "D",
        },
    }
)

DATASET = Dataset(
    {
        "path": {
            "train": "s3://gluonts-run-tool/gluon_ts_datasets/constant/train/data.json",
            "test": "s3://gluonts-run-tool/gluon_ts_datasets/constant/test/data.json",
        }
    }
)

EXPERIMENT = Experiment(ALGORITHM, DATASET)


def test_algorithm_mul_algorithm():
    with pytest.raises(TypeError):
        ALGORITHM * ALGORITHM


def test_algorithm_mul_algorithms():
    with pytest.raises(TypeError):
        ALGORITHM * Algorithms([ALGORITHM])


def test_dataset_mul_dataset():
    with pytest.raises(TypeError):
        DATASET * DATASET


def test_dataset_mul_datasets():
    with pytest.raises(TypeError):
        DATASET * Datasets([DATASET])


def test_algorithm_mul_dataset():
    assert ALGORITHM * DATASET == Experiments([EXPERIMENT])
    assert DATASET * ALGORITHM == Experiments([EXPERIMENT])


def test_algorithm_mul_datasets():
    assert ALGORITHM * Datasets([DATASET]) == Experiments([EXPERIMENT])
    assert Datasets([DATASET]) * ALGORITHM == Experiments([EXPERIMENT])


def test_algorithm_plus_algorithm():
    assert ALGORITHM + ALGORITHM == Algorithms([ALGORITHM, ALGORITHM])


def test_algorithm_plus_algorithms():
    assert ALGORITHM + Algorithms([ALGORITHM, ALGORITHM]) == Algorithms(
        [ALGORITHM, ALGORITHM, ALGORITHM]
    )
    assert Algorithms([ALGORITHM, ALGORITHM]) + ALGORITHM == Algorithms(
        [ALGORITHM, ALGORITHM, ALGORITHM]
    )
