from typing import Any, List

from pydantic import BaseModel


class Versions(BaseModel):
    __root__: List[Any]

    def __repr__(self):
        return f"Versions({self.__root__})"

    def __getitem__(self, item):
        return self.__root__[item]

    def __len__(self):
        return len(self.__root__)

    def __iter__(self):
        return iter(self.__root__)


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
