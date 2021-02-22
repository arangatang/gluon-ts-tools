from typing import Iterable
import boto3


class JobsDispatcher:
    def __init__(self, session: boto3.Session):
        self.client = session.client("sagemaker")

    def dispatch(self, jsons: Iterable[dict]):
        raise NotImplementedError
