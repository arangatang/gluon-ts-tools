from functools import partial
from typing import Any, List, Union


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
    """
    The `Node` class contains logic common to the `Algorithm` and `Dataset` classes.
    """

    def __repr__(self):
        return f"{type(self).__name__}({dict(self)})"

    def __mul__(self, other):
        """
        Calculates the cartesian product combining a `Node` with a `Node` or `ListNode`.
        This returns an Experiments object with all the combinations of this `Node`
        and the items in `other`.
        """
        if isinstance(other, Node):
            return Experiments([Experiment(self, other)])
        elif isinstance(other, ListNode):
            return Experiments([Experiment(self, item) for item in other])

        raise TypeError(f"Unable to multiply {type(self)} with {type(other)}")

    def __add__(self, other, result_type=list):
        """
        Merges multiple instances of the same Node type into an instance of
        the class `result_type`. This allows any children which inherits this
        node to add by setting the `result_type` variable to another value.
        """
        if isinstance(other, type(self)):
            return result_type([self, other])
        elif isinstance(other, result_type):
            return result_type([self]) + other

        raise TypeError


class ListNode(list):
    """
    The ListNode is the base class of the
    `Algorithms`, `Datasets` and `Experiments` classes.
    This class contains logic for adding and multiplying `Nodes`
    and `ListNodes` with eachother.
    """

    def __repr__(self):
        child_names = ", ".join([str(child) for child in self])
        return f"{type(self).__name__}({child_names})"

    def __add__(self, other):
        """
        Returns a new `ListNode` containing `other` appended to `self`.
        """
        if isinstance(other, type(self)):
            return type(self)(list(self) + list(other))
        elif isinstance(other, Node):
            return type(self)(list(self) + [other])

        raise TypeError

    def __mul__(self, other):
        """
        Calculates the cartesian product of items in
        `self` and `other` and returns an `Experiment` object
        with the results.
        """
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
        self.__add__ = partial(super().__add__, result_type=Algorithms)

    @classmethod
    def verify(cls, data: dict) -> bool:
        return (
            isinstance(data, dict)
            and isinstance(data.get("image", None), str)
            and isinstance(data.get("instance", None), str)
            and isinstance(data.get("hyperparameters", {}), dict)
        )


class Algorithms(ListNode):
    def __init__(self, data):
        if not self.verify(data):
            raise TypeError

        self.extend(Algorithm(algo) for algo in data)

    @classmethod
    def verify(cls, data):
        if not data:
            return False
        return all(map(Algorithm.verify, data))


class Dataset(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__add__ = partial(super().__add__, result_type=Datasets)

    @classmethod
    def verify(cls, data: dict) -> bool:
        return (
            isinstance(data, dict)
            and isinstance(data.get("path", None), dict)
            and isinstance(data.get("meta", {}), dict)
        )


class Datasets(ListNode):
    def __init__(self, data):
        if not self.verify(data):
            raise TypeError

        self.extend(Dataset(ds) for ds in data)

    @classmethod
    def verify(cls, data):
        if not data:
            return False
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

        if not Experiment.verify(self):
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

        self.extend(
            item
            if isinstance(item, Experiment)
            else Experiment(item["algorithm"], item["dataset"])
            for item in experiments
        )

    @classmethod
    def verify(cls, data: dict) -> bool:
        return all(map(Experiment.verify, data))

    __mul__ = None  # Several Experiments cannot be multiplied
