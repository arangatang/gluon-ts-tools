from typing import Any, List

from pydantic import BaseModel


class Versions(BaseModel):
    """
    The `Versions` class is used to represent an object which can
    take several different values.

    There are two ways of instantiating the `Versions` object, both require
    a list with the different values which the `Versions` should represent.

    >>> Versions.parse_obj([1, 2, 3])
    Versions([1, 2, 3])

    >>> Versions(__root__=[1, 2, 3])
    Versions([1, 2, 3])
    """

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
    """
    The `DotDict` class allows accessing items in a dict using a
    dot syntax.

    >>> dotdict = DotDict({"a":{"b":"hello"}})
    >>> dotdict.a.b
    'hello'
    """

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
