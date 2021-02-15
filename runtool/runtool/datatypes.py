from functools import partial
from typing import Any, List, Union, Iterable


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
        <class 'runtool.datatypes.DotDict'>
        >>> type(dotdict.a.b.c[1])
        <class 'runtool.datatypes.DotDict'>
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


class ListNode(list):
    """
    A ListNode is a python list which can be added and multiplied
    with other `Node` and `ListNode` objects.

    NOTE:
        The ListNode is meant to be subclassed by the
        `Algorithms`, `Datasets` and `Experiments` classes.

    One can add a ListNode with another ListNode in order to get
    a new ListNode with the contents of the two.

    >>> my_listnode = ListNode([Node({"hi": "there"})])
    >>> my_listnode + my_listnode
    ListNode([Node({'hi': 'there'}), Node({'hi': 'there'})])

    It is also possible to add a Node to a ListNode
    >>> my_listnode + Node({})
    ListNode([Node({'hi': 'there'}), Node({})])

    The addition is not commutative so ordering matters.
    >>> Node({}) + my_listnode
    ListNode([Node({}), Node({'hi': 'there'})])

    If two ListNodes are multiplied they generate an Experiments object
    containing the cartesian product of all the items within the two ListNodes.

    NOTE:
        Experiment objects requires an `Algorithm` and `Dataset` object,
        otherwise an error is thrown. For help understanding the example
        below, please refer to the documentation for `Algorithm`,
        `Dataset`, `Experiment` and `Experiments`.

    >>> algorithms = ListNode(
    ...     [
    ...         Algorithm({"image": "1", "instance": "1"}),
    ...         Algorithm({"image": "2", "instance": "2"}),
    ...     ]
    ... )
    >>> datasets = ListNode(
    ...     [
    ...         Dataset({"path": {"1": "1"}}),
    ...         Dataset({"path": {"2": "2"}}),
    ...     ]
    ... )
    >>> algorithms * datasets == Experiments(
    ...     [
    ...         Experiment(
    ...             Algorithm({"image": "1", "instance": "1"}),
    ...             Dataset({"path": {"1": "1"}}),
    ...         ),
    ...         Experiment(
    ...             Algorithm({"image": "1", "instance": "1"}),
    ...             Dataset({"path": {"2": "2"}}),
    ...         ),
    ...         Experiment(
    ...             Algorithm({"image": "2", "instance": "2"}),
    ...             Dataset({"path": {"1": "1"}}),
    ...         ),
    ...         Experiment(
    ...             Algorithm({"image": "2", "instance": "2"}),
    ...             Dataset({"path": {"2": "2"}}),
    ...         ),
    ...     ]
    ... )
    True
    """

    def __repr__(self) -> str:
        child_names = ", ".join([str(child) for child in self])
        return f"{type(self).__name__}([{child_names}])"

    def __add__(self, other) -> Any:
        """
        Returns a new `ListNode` (or any subclass) with `other` appended to `self`.
        """
        if isinstance(other, type(self)):
            return type(self)(list(self) + list(other))
        elif isinstance(other, Node):
            return type(self)(list(self) + [other])

        raise TypeError

    def __mul__(self, other) -> "Experiments":
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


class Experiments(ListNode):
    """
    The `Experiments` class contains a set of `Experiment` objects.
    Essentially, this class corresponds to a set of experiments one
    wish to execute.
    An `Experiments` object can be added with another `Experiment` object

    >>> experiments = Experiments(
    ...     [
    ...         Experiment(
    ...             Algorithm({"image": "1", "instance": "1"}),
    ...             Dataset({"path": {"1": "1"}}),
    ...         )
    ...     ]
    ... )
    >>> len(experiments + experiments + experiments)
    3
    """

    def __init__(self, experiments: Union[List[dict], List["Experiment"]]):
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


class Datasets(ListNode):
    """
    The Datasets class contains a set of Dataset objects.
    >>> datasets = Datasets([Dataset({"path": {}})])
    >>> len(datasets)
    1

    A `Datasets` object can be added with another `Datasets` object
    to merge them into a new `Datasets` object.
    >>> len(datasets + datasets)
    2

    `Dataset` objects can be added to a `Datasets` object.
    >>> len(datasets + datasets + Dataset({"path": {}}))
    3

    `Datasets` can be multiplied with `Algorithms` and `Algorithm` objects to
    form `Experiments`.

    >>> algorithms = Algorithms(
    ...     [
    ...         Algorithm({"image": "1", "instance": "1"}),
    ...         Algorithm({"image": "2", "instance": "2"}),
    ...     ]
    ... )
    >>> datasets = Datasets(
    ...     [
    ...         Dataset({"path": {"1": "1"}}),
    ...         Dataset({"path": {"2": "2"}}),
    ...     ]
    ... )
    >>> datasets * algorithms == Experiments(
    ...     [
    ...         Experiment(
    ...             Algorithm({"image": "1", "instance": "1"}),
    ...             Dataset({"path": {"1": "1"}}),
    ...         ),
    ...         Experiment(
    ...             Algorithm({"image": "2", "instance": "2"}),
    ...             Dataset({"path": {"1": "1"}}),
    ...         ),
    ...         Experiment(
    ...             Algorithm({"image": "1", "instance": "1"}),
    ...             Dataset({"path": {"2": "2"}}),
    ...         ),
    ...         Experiment(
    ...             Algorithm({"image": "2", "instance": "2"}),
    ...             Dataset({"path": {"2": "2"}}),
    ...         ),
    ...     ]
    ... )
    True
    """

    def __init__(self, iterable: Iterable):
        if not self.verify(iterable):
            raise TypeError

        self.extend(Dataset(ds) for ds in iterable)

    @classmethod
    def verify(cls, data: Any) -> bool:
        if not data:
            return False

        return all(map(Dataset.verify, data))


class Algorithms(ListNode):
    """
    The `Algorithms` class contains a set of `Algorithm` objects.
    >>> algorithms = Algorithms([Algorithm({"image": "", "instance": ""})])
    >>> len(algorithms)
    1

    A `Algorithms` object can be added with another `Algorithms` object
    to merge them into a new `Algorithms` object.
    >>> len(algorithms + algorithms)
    2

    `Algorithm` objects can be added to an `Algorithm` object.
    >>> len(algorithms + algorithms + Algorithm({"image": "", "instance": ""}))
    3

    `Algorithms` can be multiplied with `Datasets` and `Dataset` objects to
    form `Experiments` objects.

    >>> algorithms = Algorithms(
    ...     [
    ...         Algorithm({"image": "1", "instance": "1"}),
    ...         Algorithm({"image": "2", "instance": "2"}),
    ...     ]
    ... )
    >>> datasets = Datasets(
    ...     [
    ...         Dataset({"path": {"1": "1"}}),
    ...         Dataset({"path": {"2": "2"}}),
    ...     ]
    ... )
    >>> algorithms * datasets == Experiments(
    ...     [
    ...         Experiment(
    ...             Algorithm({"image": "1", "instance": "1"}),
    ...             Dataset({"path": {"1": "1"}}),
    ...         ),
    ...         Experiment(
    ...             Algorithm({"image": "1", "instance": "1"}),
    ...             Dataset({"path": {"2": "2"}}),
    ...         ),
    ...         Experiment(
    ...             Algorithm({"image": "2", "instance": "2"}),
    ...             Dataset({"path": {"1": "1"}}),
    ...         ),
    ...         Experiment(
    ...             Algorithm({"image": "2", "instance": "2"}),
    ...             Dataset({"path": {"2": "2"}}),
    ...         ),
    ...     ]
    ... )
    True
    """

    def __init__(self, data):
        if not self.verify(data):
            raise TypeError

        self.extend(Algorithm(algo) for algo in data)

    @classmethod
    def verify(cls, data) -> bool:
        if not data:
            return False
        return all(map(Algorithm.verify, data))


class Node(dict):
    """
    A `Node` is a dictionary which can be added and multiplied.
    Per default

    NOTE:
        This class is meant to be subclassed by the:
        `Algorithm`, `Dataset` and `Experiment` classes.

    >>> my_node = Node({"hello": "world"})

    Per default, a node added to another node produces a ListNode
    containing the two nodes.

    >>> my_node + my_node
    ListNode([Node({'hello': 'world'}), Node({'hello': 'world'})])

    If two nodes are multiplied they generate an Experiments object
    with one item.

    NOTE:
        Experiment objects requires an `Algorithm` and `Dataset` object,
        otherwise an error is thrown.
        Please refer to the documentation for `Algorithm` and
        `Dataset` for examples of multiplication of `Node` objects.
    """

    result_type = ListNode

    def __repr__(self) -> str:
        return f"{type(self).__name__}({dict(self)})"

    def __mul__(self, other) -> "Experiments":
        """
        Calculates the cartesian product combining a `Node` with a `Node` or `ListNode`
        and returns an `Experiment` object containing the result.
        """
        if isinstance(other, Node):
            return Experiments([Experiment(self, other)])
        elif isinstance(other, ListNode):
            return Experiments([Experiment(self, item) for item in other])

        raise TypeError(f"Unable to multiply {type(self)} with {type(other)}")

    def __add__(self, other) -> Any:
        """
        Merges multiple instances of the same Node type into an instance of
        the class passed to the `result_type` parameter.
        This allows any classes inheriting from `Node` to customize the
        return type of __add__ without redefining the logic.

        NOTE::
            The result_type needs to take a `list` as an __init__ parameter
            and it has to have the __add__ method implemented.
        """
        if isinstance(other, type(self)):
            return self.result_type([self, other])
        elif isinstance(other, self.result_type):
            return self.result_type([self]) + other

        raise TypeError


class Algorithm(Node):
    """
    The `Algorithm` class represents a single algorithm in a config file.
    The class contains rules for identifying if an object has the
    correct structure to be an `Algorithm` as well as logic for
    multiplication and addition.

    Two `Algorithm` objects can be added together to form a
    `Algorithms` object.

    >>> algorithm = Algorithm({"image": "", "instance": ""})
    >>> algorithm + algorithm
    Algorithms([Algorithm({'image': '', 'instance': ''}), Algorithm({'image': '', 'instance': ''})])

    An `Algorithm` can be multiplied with a `Dataset` object to form an
    `Experiments` object.

    >>> algorithm * Dataset({"path": {}})
    Experiments([Experiment({'algorithm': Algorithm({'image': '', 'instance': ''}), 'dataset': Dataset({'path': {}})})])

    An Algorithm can also be multiplied with a Dataset object in order to
    form several experiments at once.
    >>> algorithm * Datasets(
    ...     [{"path": {"1": ""}}, {"path": {"2": ""}}]
    ... ) == Experiments(
    ...     [
    ...         Experiment(
    ...             Algorithm({"image": "", "instance": ""}),
    ...             Dataset({"path": {"1": ""}}),
    ...         ),
    ...         Experiment(
    ...             Algorithm({"image": "", "instance": ""}),
    ...             Dataset({"path": {"2": ""}}),
    ...         ),
    ...     ]
    ... )
    True
    """

    # set that Algorithms should be generated when
    # adding two Algorithm objects
    result_type = Algorithms

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not Algorithm.verify(self):
            raise TypeError

    @classmethod
    def verify(cls, data: dict) -> bool:
        """
        Determines if data has the structure needed to be an Algorithm.
        An Algorithm is defined as being a dictionary with atleast
        these two keys:

        - image
        - instance

        >>> Algorithm.verify({"a": "b"})
        False
        >>> Algorithm.verify({"image": "", "instance": ""})
        True

        Furthermore, an additional key "hyperparameters" needs to
        be of type dict if hyperparameters exists in the data.
        >>> Algorithm.verify({"image": "", "instance": "", "hyperparameters": {}})
        True
        >>> Algorithm.verify({"image": "", "instance": "", "hyperparameters": ""})
        False
        """
        return (
            isinstance(data, dict)
            and isinstance(data.get("image", None), str)
            and isinstance(data.get("instance", None), str)
            and isinstance(data.get("hyperparameters", {}), dict)
        )


class Dataset(Node):
    """
    The `Dataset` class represents a single dataset in a config file.
    The class contains rules for identifying if an object has the
    correct structure to be a `Dataset` as well as logic for
    multiplication and addition.

    Two `Dataset` objects can be added together to form a
    `Datasets` object.

    >>> dataset = Dataset({"path": {}})
    >>> dataset + dataset
    Datasets([Dataset({'path': {}}), Dataset({'path': {}})])

    An `Algorithm` can be multiplied with a `Dataset` object
    to form an `Experiments` object.

    >>> dataset * Algorithm({"image": "", "instance": ""})
    Experiments([Experiment({'algorithm': Algorithm({'image': '', 'instance': ''}), 'dataset': Dataset({'path': {}})})])

    A `Dataset` can also be multiplied with a `Algorithms` object in order to
    form several `Experiment` objects at once.

    >>> dataset * Algorithms(
    ...     [
    ...         {"image": "1", "instance": "1"},
    ...         {"image": "2", "instance": "2"},
    ...     ]
    ... ) == Experiments(
    ...     [
    ...         Experiment(
    ...             Algorithm({"image": "1", "instance": "1"}),
    ...             Dataset({"path": {}}),
    ...         ),
    ...         Experiment(
    ...             Algorithm({"image": "2", "instance": "2"}),
    ...             Dataset({"path": {}}),
    ...         ),
    ...     ]
    ... )
    True
    """

    # set that Datasets should be generated when
    # adding two Dataset objects
    result_type = Datasets

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not Dataset.verify(self):
            raise TypeError

    @classmethod
    def verify(cls, data: dict) -> bool:
        return (
            isinstance(data, dict)
            and isinstance(data.get("path", None), dict)
            and isinstance(data.get("meta", {}), dict)
        )


class Experiment(Node):
    """
    The Experiment class represents a combination of an
    algorithm that is to be run on a dataset. This class
    verifies that the parameters passed to it upon
    instantiation could be parsed be an Algorithm and a Dataset.

    Two experiments can be added to form a `Experiments` object.

    >>> experiment = Experiment(
    ...     Algorithm({"image": "", "instance": ""}),
    ...     Dataset({"path": {}}),
    ... )
    >>> type(experiment + experiment)
    <class 'runtool.datatypes.Experiments'>
    """

    # set that Experiments should be generated when
    # adding two Experiment objects
    result_type = Experiments

    def __init__(
        self,
        node_1: Union[Algorithm, Dataset],
        node_2: Union[Algorithm, Dataset],
    ):
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
    def verify(cls, data: dict) -> bool:
        return Algorithm.verify(data["algorithm"]) and Dataset.verify(
            data["dataset"]
        )

    __mul__ = None  # An Experiment cannot be multiplied
