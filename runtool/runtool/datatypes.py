from typing import Any, List, Union, Dict


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


class Node(dict):
    def __repr__(self):
        return f"{type(self).__name__}({self.items()})"

    def __mul__(self, other):
        if isinstance(other, Node):
            return Experiments([Experiment(self, other)])
        elif isinstance(other, ListNode):
            return Experiments([Experiment(self, item) for item in other])

        raise TypeError(f"Unable to multiply {type(self)} with {type(other)}")

    def __add__(self, other):
        if isinstance(other, type(self)):
            return self.__add_result_class__([self, other])
        elif isinstance(other, self.__add_result_class__):
            return self.__add_result_class__([self]) + other

        raise TypeError


class ListNode(list):
    def __repr__(self):
        child_names = ", ".join([str(child) for child in self])
        return f"{type(self).__name__}({child_names})"

    def __add__(self, other):
        if isinstance(other, type(self)):
            return type(self)(list(self) + list(other))
        elif isinstance(other, self.allowed_children):
            return type(self)(list(self) + [other])

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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__add_result_class__ = Algorithms

    @classmethod
    def verify(cls, data: dict) -> bool:
        return all(
            (
                isinstance(data, dict),
                isinstance(data.get("image", None), str),
                isinstance(data.get("instance", None), str),
                isinstance(data.get("hyperparameters", {}), dict),
            )
        )


class Algorithms(ListNode):
    def __init__(self, data):
        if not self.verify(data):
            raise TypeError

        self.extend(Algorithm(algo) for algo in data)
        self.allowed_children = Algorithm
        self.multiplies_with = (Dataset, Datasets)

    @classmethod
    def verify(cls, data):
        return all(map(Algorithm.verify, data))


class Dataset(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__add_result_class__ = Datasets

    @classmethod
    def verify(cls, data: dict) -> bool:
        return all(
            (
                isinstance(data, dict),
                isinstance(data.get("path", None), dict),
                isinstance(data.get("meta", {}), dict),
            )
        )


class Datasets(ListNode):
    def __init__(self, data):
        if not self.verify(data):
            raise TypeError

        self.extend(Dataset(ds) for ds in data)
        self.allowed_children = Dataset
        self.multiplies_with = (Algorithm, Algorithms)

    @classmethod
    def verify(cls, data):
        return all(map(Dataset.verify, data))


class Experiment(dict):
    def __init__(self, node_1, node_2):
        def extract(desired_type):
            if isinstance(node_1, desired_type):
                return node_1
            elif isinstance(node_2, desired_type):
                return node_2
            return None

        self["algorithm"] = extract(Algorithm)
        self["dataset"] = extract(Dataset)
        if not (self["dataset"] and self["algorithm"]):
            raise TypeError(
                "An Experiment requires a Dataset and an Algorithm, got:"
                f"{type(node_1)} and {type(node_2)}"
            )

    @classmethod
    def verify(cls, data):
        return Algorithm.verify(data["algorithm"]) and Dataset.verify(
            data["dataset"]
        )

    __mul__ = None  # An Experiment cannot be multiplied


class Experiments(ListNode):
    def __init__(self, experiments: Union[List[dict], List[Experiment]]):
        if not self.verify(experiments):
            raise TypeError

        for item in experiments:
            if not isinstance(item, Experiment):
                item = Experiment(item["algorithm"], item["dataset"])
            self.append(item)

        self.allowed_children = Experiment

    @classmethod
    def verify(cls, data: dict) -> bool:
        return all(map(Experiment.verify, data))

    __mul__ = None  # Several Experiments cannot be multiplied
