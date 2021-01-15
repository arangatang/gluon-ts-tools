from pydantic import BaseModel
from typing import Any, List


class Versions(BaseModel):
    versions: List

    def __repr__(self):
        return f"Versions({self.versions})"

    def __getitem__(self, key):
        return self.versions[key]

    def __len__(self):
        return len(self.versions)


class DotDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __init__(self, init_data={}):
        assert isinstance(init_data, dict)
        for key, value in init_data.items():
            if hasattr(value, "keys"):
                if isinstance(value, DotDict):
                    self[key] = value
                else:
                    self[key] = DotDict(value)
            else:
                self[key] = value
