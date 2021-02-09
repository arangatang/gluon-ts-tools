from typing import Any, List


class Versions:
    """
    The `Versions` class is used to represent an object which can
    take several different values. These different values are passed
    as a list when initializing the Versions object.

    >>> Versions([1, 2, 3])
    Versions([1, 2, 3])
    """

    def __init__(self, versions: list):
        assert isinstance(versions, list)
        self.__root__ = versions

    def __repr__(self):
        return f"Versions({self.__root__})"

    def __getitem__(self, item):
        return self.__root__[item]

    def __len__(self):
        return len(self.__root__)

    def __iter__(self):
        return iter(self.__root__)

    def __eq__(self, other):
        if not isinstance(other, Versions):
            return False

        if len(other) != len(self):
            return False

        # enforce same ordering and equality of children
        for this_version, other_version in zip(self.__root__, other.__root__):
            if this_version != other_version:
                return False

        return True

    def append(self, data: Any):
        self.__root__.append(data)

    def __contains__(self, data: Any) -> bool:
        return data in self.__root__


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

    def as_dict(self) -> dict:
        """
        Converts the DotDict into a python `dict` recursively.

        >>> dotdict = DotDict({"a": {"b": {"c": [0, DotDict({"d": 1})]}}})
        >>> type(dotdict)
        <class 'datatypes.DotDict'>
        >>> type(dotdict.a.b.c[1])
        <class 'datatypes.DotDict'>
        >>> as_dict = dotdict.as_dict()
        >>> type(as_dict)
        <class 'dict'>
        >>> type(as_dict["a"]["b"]["c"][1])
        <class 'dict'>
        """

        def convert(value: Any) -> Any:
            if isinstance(value, DotDict):
                return value.as_dict()
            elif isinstance(value, list):
                return list(map(convert, value))
            else:
                return value

        return {key: convert(value) for key, value in self.items()}


class Node(DotDict):
    def __repr__(self):
        return f"{type(self).__name__}({self.items()})"


class ListNode(list):
    def __repr__(self):
        child_names = ", ".join([str(child) for child in self])
        return f"{type(self).__name__}({child_names})"

    def __add__(self, other):
        if isinstance(other, type(self)):
            return type(self)(list(self) + list(other))
        elif isinstance(other, self.allowed_children):
            return type(self)(list(self) + [other])
        else:
            raise TypeError

    def __mul__(self, other):
        if isinstance(other, self.multiplies_with):
            if isinstance(other, ListNode):
                return Experiments(
                    [
                        Experiment(node_1, node_2)
                        for node_1 in self
                        for node_2 in other
                    ]
                )
            elif isinstance(other, Node):
                return Experiments([Experiment(item, other) for item in self])

        raise TypeError


class Algorithm(Node):
    @classmethod
    def verify(cls, data):
        try:
            assert "image" in data
            assert "instance" in data
            assert isinstance(data.get("hyperparameters", {}), dict)
            return True
        except AssertionError:
            return False

    def __mul__(self, other):
        if type(other) is Dataset:
            return Experiments([Experiment(self, other)])
        elif type(other) is Datasets:
            return Experiments([Experiment(self, ds) for ds in other])
        else:
            raise TypeError(f"Unable to multiply Algorithm with {type(other)}")

    def __add__(self, other):
        if isinstance(other, Algorithm):
            return Algorithms([self, other])
        elif isinstance(other, Algorithms):
            return Algorithms([self]) + other
        else:
            raise TypeError


class Algorithms(ListNode):
    def __init__(self, data):
        if not self.verify(data):
            raise TypeError

        for algo in data:
            self.append(Algorithm(algo))

        self.allowed_children = Algorithm
        self.multiplies_with = (Dataset, Datasets)

    @classmethod
    def verify(cls, data):
        for item in data:
            if not Algorithm.verify(item):
                return False
        return True


class Dataset(Node):
    @classmethod
    def verify(cls, data):
        try:
            assert data["path"]
            assert isinstance(data["path"], dict)
            assert isinstance(data.get("meta", {}), dict)
            return True
        except Exception:
            return False

    def __mul__(self, other):
        if isinstance(other, Algorithm):
            return Experiments([Experiment(other, self)])
        elif isinstance(other, Algorithms):
            return Experiments([Experiment(algo, self) for algo in other])
        else:
            raise TypeError

    def __add__(self, other):
        if type(other) is Dataset:
            return Datasets([self, other])
        elif type(other) is Datasets:
            return Datasets([self]) + other
        else:
            raise TypeError


class Datasets(ListNode):
    allowed_children = Dataset

    def __init__(self, data):
        if not self.verify(data):
            raise TypeError
        for ds in data:
            self.append(Dataset(ds))

        self.allowed_children = Dataset
        self.multiplies_with = (Algorithm, Algorithms)

    @classmethod
    def verify(cls, data):
        for item in data:
            if not Dataset.verify(item):
                return False
        return True


class Experiment(Node):
    def __init__(self, node_1, node_2):
        def extract(desired_type):
            if isinstance(node_1, desired_type):
                return node_1
            elif isinstance(node_2, desired_type):
                return node_2
            return None

        self["algorithm"] = extract(Algorithm)
        self["dataset"] = extract(Dataset)
        assert self["dataset"] and self["algorithm"]

    @classmethod
    def verify(cls, data):
        try:
            assert Algorithm.verify(data["algorithm"])
            assert Dataset.verify(data["dataset"])
            return True
        except Exception:
            return False


class Experiments(ListNode):
    def __init__(self, experiments):
        if not self.verify(experiments):
            raise TypeError

        for item in experiments:
            if not isinstance(item, Experiment):
                item = Experiment(item["algorithm"], item["dataset"])
            self.append(item)

        self.allowed_children = Experiment
        self.multiplies_with = None

    @classmethod
    def verify(cls, data):
        for item in data:
            if not Experiment.verify(item):
                print(f"expected an Experiment, found {type(item)}")
                return False
        return True
