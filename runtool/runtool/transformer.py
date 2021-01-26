import itertools
import math
import re
import json
from functools import partial, singledispatch
from typing import Any, Callable, Tuple, Union
from uuid import uuid4

from runtool.datatypes import DotDict, Versions
from runtool.utils import get_item_from_path, update_nested_dict


@singledispatch
def recursive_apply(node, fn: Callable) -> Any:
    """
    Applies a function to `dict` nodes in a JSON-like structure.
    The node that the function is applied to will be replaced with what
    `fn` returns. If the `fn` generates `runtool.datatypes.Versions`
    objects are merged into a new `runtool.datatypes.Versions` object
    and returned.

    NOTE::
        `runtool.datatypes.Versions` represents different versions of an object.

    In the following examples we will transform a JSON structure using
    the `transform` function defined below.

    >>> def transform(node):
    ...     '''
    ...     Converts node to a version object or multiplies it by 2
    ...     '''
    ...     if "version" in node:
    ...         return Versions(node["version"])
    ...     if "double" in node:
    ...         return 2 * node["double"]
    ...     return node

    Below is a simple example where the node is replaced with 2 after `transform`
    is applied to it.

    >>> recursive_apply(
    ...     {"double": 1},
    ...     fn = transform
    ... )
    2

    If the JSON structure contains nested nodes, `recursive_apply` applies `fn`
    to each `dict` node in the tree and replaces the node with whatever `fn` returns.

    >>> recursive_apply(
    ...     {
    ...         "no_double": 2,
    ...         "double_this": {
    ...             "double": 2
    ...         },
    ...     },
    ...     fn = transform
    ... )
    {'no_double': 2, 'double_this': 4}

    In the below example two `runtool.datatypes.Versions` will be created by
    the `transform` function. `recursive_apply` merges these and thus the result
    of `recursive_apply` will here be a `runtool.datatypes.Versions` object.

    >>> result = recursive_apply(
    ...     {
    ...         "my_list": [
    ...             {"hello": "there"},
    ...             {"a": {"version": [1, 2]}},
    ...             {"b": {"version": [3, 4]}},
    ...         ]
    ...     },
    ...     fn = transform
    ... )
    >>> type(result)
    <class 'runtool.datatypes.Versions'>
    >>> for version in result:
    ...     print(version)
    {'my_list': [{'hello': 'there'}, {'a': 1}, {'b': 3}]}
    {'my_list': [{'hello': 'there'}, {'a': 1}, {'b': 4}]}
    {'my_list': [{'hello': 'there'}, {'a': 2}, {'b': 3}]}
    {'my_list': [{'hello': 'there'}, {'a': 2}, {'b': 4}]}

    """
    return node


@recursive_apply.register
def recursive_apply_dict(node: dict, fn: Callable) -> Any:
    """
    Applies `fn` to each element in the dict, if `fn` changes the node,
    the changes should be returned. If the `fn` foes not change the node,
    it calls `recursive_apply` on the children of the node.

    In case the recursion on the children results in one or more
    `runtool.datatypes.Versions` objects, the cartesian product of these
    versions is calculated and a new `runtool.datatypes.Versions` object will be
    returned containing the different versions of this node.

    """
    # basecase of recursion, if `fn` modifies the node, return the new node
    new_node = fn(node)
    if new_node is not node:
        return new_node

    # else merge children of type Versions into a new Versions object
    expanded_children = []
    new_node = {}
    for key in node:
        child = recursive_apply(node[key], fn)
        if isinstance(child, Versions):
            # If the child is a Versions object, map the key to all its versions
            # example:
            # child = Versions([1,2]),
            # key=['a']
            #
            # results in
            #
            # (('a':1), ('a':2))
            expanded_children.append(itertools.product([key], child))
        else:
            new_node[key] = child

    if expanded_children:
        # example:
        # expanded_children = [(('a':1), ('a':2)), (('b':1), ('b':2))]
        # new_node = {"c": 3}
        #
        # results in:
        #
        # Versions([
        #   {'a':1, 'b':1, 'c':3},
        #   {'a':1, 'b':2, 'c':3},
        #   {'a':2, 'b':1, 'c':3},
        #   {'a':3, 'b':2, 'c':3},
        # ])
        return Versions(
            [
                dict(version_of_node, **new_node)
                for version_of_node in itertools.product(*expanded_children)
            ]
        )

    return new_node


@recursive_apply.register
def recursive_apply_list(node: list, fn: Callable) -> Any:
    """
    Calls `recursive_apply` on each element in the node, without applying `fn`.
    Calculates the cartesian product of any `runtool.datatypes.Versions` objects
    in the nodes children. From this a new `runtool.datatypes.Versions`object is
    generated representing the different variants that this node can take.

    NOTE::
        The indexes of the node are maintained throughout this process.
    """
    versions_in_children = []
    child_normal = [None] * len(node)  # maintans indexes
    for index in range(len(node)):
        child = recursive_apply(node[index], fn)
        if isinstance(child, Versions):
            # child = Versions([1,2])
            # =>
            # expanded_child_version = ((index, 1), (index, 2))
            expanded_child_version = itertools.product([index], child)
            versions_in_children.append(expanded_child_version)
        else:
            child_normal[index] = child

    if not versions_in_children:
        return child_normal

    # merge the data from the children which were not Versions objects
    # together with the data from the children which were Versions objects
    new_versions = []
    for version in itertools.product(*versions_in_children):
        new_data = child_normal[:]
        for index, value in version:
            new_data[index] = value
        new_versions.append(new_data)

    return Versions(new_versions)


def apply_from(node: dict, data: dict) -> dict:
    """
    Update the node with the data which the path in node['$from'] is pointing to.
    i.e.

    >>> apply_from(
    ...     node = {"$from": "another_node.a_key", "some_key": "some_value"},
    ...     data = {"another_node": {"a_key": {"hello": "world"}}}
    ... )
    {'hello': 'world', 'some_key': 'some_value'}

    """
    node = dict(**node)  # needed if $from reference another $from
    path = node.pop("$from")
    from_value = get_item_from_path(data, path)
    from_value = recursive_apply(from_value, partial(do_from, context=data))

    assert isinstance(
        from_value, dict
    ), "$from can only be used to inherit from a dict"
    from_value = update_nested_dict(from_value, node)
    return dict(**from_value)


def apply_ref(node: dict, context: dict) -> Any:
    """
    If the node contains a `$ref`, resolve any nested `$ref` which node["$ref"]
    points to in the `context`. Thereafter replace the current node with the
    resolved value.

    In the below example, we want to replace the node with the value of
    `context["some_node"][0]["some_val"]`. This, however references
    `context["target"]` thus the value which the node will be replaced with
    will be `1` when the nested references has been resolved.

    >>> apply_ref(
    ...     node={"$ref": "some_node.0.some_val"},
    ...     context = {
    ...         "target": 1,
    ...         "some_node": [
    ...             {"some_val": {"$ref": "target"}},
    ...             "ignored"
    ...         ]
    ...     }
    ... )
    1
    """
    assert len(node) == 1, "$ref needs to be the only value"
    data = get_item_from_path(context, node["$ref"])
    return recursive_apply(data, partial(do_ref, context=context))


def evaluate(text: str, locals: dict) -> Any:
    """
    Performs the python function `eval` on the text.
    The text will have access to the values in the parameter `locals`
    when `eval` is applied. Further functionality such as a unique id `uid`
    as well as the `math` package is available when evaluating the text.

    >>> evaluate(
    ...     "len(uid) + pow(some_value, 2)",
    ...     {"some_value": 2}
    ... )
    16.0
    """
    uid = str(uuid4()).split("-")[-1]
    locals = dict(DotDict(locals))
    globals = {**math.__dict__, "uid": uid}
    ret = eval(
        text,
        globals,
        locals,
    )
    if isinstance(ret, dict) and "$eval" in ret:
        return do_eval(ret, locals)
    return ret


def recurse_eval(path: str, data: dict, fn: Callable) -> Tuple[str, Any]:
    """
    Given a `path` to fetch from in the `data`, this function identifies
    which parts of the path are actually in the `data` and what parts are
    attributes of the value which will be extracted.
    furthermore, this function calls `fn` on the data extracted from `data`
    and returns the result.

    In the following example, `a.b.0` is identified as the path to return
    since `.split()` is not an item in `data`.

    >>> recurse_eval(
    ...     path = "a.b.0.split(' ')",
    ...     data = {"a": {"b": [{"$eval": "'hey ' * 2"}]}},
    ...     fn = lambda node, _ : eval(node["$eval"]) if "$eval" in node else node
    ... )
    ('a.b.0', 'hey hey ')
    """
    tmp = data
    current_path = []
    path = path.replace("[", ".[")
    for key in path.split("."):
        original_key = key
        if "[" in key:
            key = key.replace("[", "").replace("]", "").replace('"', "")
        try:
            tmp = tmp[key]
            current_path.append(original_key)
        except TypeError:
            try:
                tmp = tmp[int(key)]
                current_path.append(original_key)
            except ValueError:
                break
        except:
            break
    return ".".join(current_path).replace(".[", "["), fn(tmp, data)


def apply_eval(node: dict, locals: dict) -> Any:
    """
    Evaluates the expression in `node["$eval"]` recursively then returns
    the result.

    The text in `node["$eval"]` can contain some keywords which `apply_eval`
    can use to preprocess the text before `eval` is run on the text.
    The following keywords are supported in the text:

    - `$`       is used to reference data in the `locals` parameters
    - `$trial`  references an experiment which is defined during runtime
                (see `apply_trial`)

    Example of when `$` is used:

    >>> apply_eval({"$eval": "2 + 5 * $.value"}, {"value": 2})
    12

    >>> apply_eval({"$eval": "$.my_key.split()"}, {"my_key": "some string"})
    ['some', 'string']

    Example of when `$trial` is used. Since we do not yet know what the `$trial`
    should resolve to we cannot calculate the value.
    Note::

        $trial gets renamed to __trial__ here as this function is a
        preprocessing step to `apply_trial`.

    >>> apply_eval({"$eval": "$trial.algorithm.some_value * 2"}, {})
    {'$eval': '__trial__.algorithm.some_value * 2'}

    """
    assert len(node) == 1, "$eval needs to be only value"
    text = str(node["$eval"])
    text = text.replace("$trial", "__trial__")

    # matches any parts of the text which is similar to this:
    # $.somestring.somotherstring[0]['a_key']["some_key"]
    regex = r"""
        (\$                         # match string starting with $ and followed by:
            (?:
                \[[\d]+\]|          # digits enclosed in [] i.e. $[0]
                \[\"[\w_\d$]+\"\]|  # words or digits in "[]" i.e. $["0"]
                \[\'[\w_\d$]+\'\]|  # words or digits in '[]' i.e. $['0']
                \.[\w_\d]+          # words or digits prepended with a dot, i.e. $.hello
            )+
        )
    """

    # replace any matched substrings of the text with whatever the
    # substrings pointed to in the locals parameter
    for match in re.finditer(regex, text, flags=re.VERBOSE):
        path, value = recurse_eval(match[0].lstrip("$."), locals, do_eval)
        path = f"$.{path}"
        if isinstance(value, dict) and "$eval" in value:
            text = text.replace(path, f"({value['$eval']})")
        elif type(value) is str:
            text = text.replace(path, f"'{value}'")
        else:
            text = text.replace(path, str(value))

    try:
        return evaluate(text, locals)
    except NameError as error:
        if "__trial__" in str(error):
            node["$eval"] = text
            return node
        else:
            raise error


def apply_trial(node: dict, locals: dict) -> Any:
    """
    Works similarly as `apply_eval` however this method only evaluates
    the parts of `node["$eval"]` which starts with __trial__.
    For more information read the documentation of `apply_eval`.

    >>> apply_trial(
    ...     {"$eval" : "2 + __trial__.something[0]"},
    ...     {"__trial__": {"something":[1,2,3]}}
    ... )
    3
    """
    assert len(node) == 1, "$eval needs to be only value"
    text = str(node["$eval"])

    regex = r"""
        (__trial__
            (?:
                \[[\d]+\]|          # digits enclosed in [] i.e. __trial__[0]
                \[\"[\w_\d$]+\"\]|  # words or digits in "[]" i.e. __trial__["0"]
                \[\'[\w_\d$]+\'\]|  # words or digits in '[]' i.e. __trial__['0']
                \.\w+[\w_\d]*       # words or digits prepended with a dot, i.e. __trial__.hell0
            )+
        )
    """

    # find longest working path for each match in locals
    for match in re.finditer(regex, text, flags=re.VERBOSE):
        substring, value = recurse_eval(match[0], locals, do_trial)

        if isinstance(value, dict) and "$eval" in value:
            raise TypeError("$eval: $trial cannot resolve to value")
        elif type(value) is str:
            text = text.replace(substring, f"'{value}'")
        else:
            text = text.replace(substring, str(value))

    return evaluate(text, locals)


def apply_each(node: dict) -> Versions:
    """
    If `$each` is in the node, it means that the node can become
    several different values.

    Example, a node which can take the values `1` or `2` or `3`:

    >>> apply_each({"$each":[1,2,3]})
    Versions([1, 2, 3])

    Below is an example where `$each` is used to generate two versions
    of the node:
    >>> apply_each(
    ...     {
    ...         "c": "dummy",
    ...         "$each": ["$None", {"a": 150, "b": 64}]
    ...     }
    ... )
    Versions([{'c': 'dummy'}, {'a': 150, 'b': 64, 'c': 'dummy'}])

    Parameters
    ----------
    node
        The node which should have `$each` applied to it.

    Returns
    -------
    runtool.datatypes.Versions
        The versions object representing the different values of the node.
    """

    each = recursive_apply(node.pop("$each"), do_each)
    if isinstance(each, list):
        # check if all are dicts or has the $None tag
        if all(
            map(lambda item: isinstance(item, dict) or item == "$None", each)
        ):
            new = []
            for item in each:
                if item == "$None":
                    new.append(node)
                else:
                    item.update(node)
                    new.append(item)
            each = new
        else:
            each = [None if item == "$None" else item for item in each]
        return Versions(each)
    elif isinstance(each, dict):
        seperated_dicts = [{key, val} for key, val in each.items()]
        for a_dict in seperated_dicts:
            a_dict.update(node)
        return Versions(seperated_dicts)
    elif isinstance(each, Versions):
        # when having a nested $each this will be triggered
        flattened = itertools.chain.from_iterable(each)
        return Versions(list(flattened))
    else:
        print("Something went wrong when expanding $each")
        raise NotImplementedError


# DO: find correct place within the data to do the transformation
def do_from(node, context):
    """
    If the node is a dict and has `"$from"` as a key calls
    `runtool.transformer.apply_from` and returns the results.
    Otherwise returns the node.
    """
    if isinstance(node, dict) and "$from" in node:
        return apply_from(node, context)
    return node


def do_ref(node, context):
    """
    If the node is a dict and has `"$ref"` as a key calls
    `runtool.transformer.apply_ref` and returns the results.
    Otherwise returns the node.
    """
    if isinstance(node, dict) and "$ref" in node:
        return apply_ref(node, context)
    return node


def do_eval(node, locals):
    """
    If the node is a dict and has `"$eval"` as a key calls
    `runtool.transformer.apply_eval` and returns the results.
    Otherwise returns the node.
    """
    if isinstance(node, dict) and "$eval" in node:
        return apply_eval(node, locals)
    return node


def do_trial(node, locals):
    """
    If the node is a dict and has `"$eval"` as a key calls
    `runtool.transformer.apply_trial` and returns the results.
    Otherwise returns the node.
    """
    if isinstance(node, dict) and "$eval" in node:
        return apply_trial(node, locals)
    return node


def do_each(node):
    """
    If the node is a dict and has `"$each"` as a key calls
    `runtool.transformer.apply_each` and returns the results.
    Otherwise returns the node.
    """
    if isinstance(node, dict) and "$each" in node:
        return apply_each(node)
    return node


def apply_transformations(data: dict) -> list:
    """
    Applies a chain of transformations converting nodes in `data` using

    - `do_from`
    - `do_eval`
    - `do_each`
    - `do_ref`

    Returns the different variants of the `data` after transformations as a list.

    >>> result = apply_transformations(
    ...    {
    ...         "base": {"msg": "hi"},
    ...         "a": {"$from": "base", "smth": {"$each": [{"$eval": "pow(7, 2)"}, 2]}},
    ...         "b": [{"$ref": "a.msg"}],
    ...     }
    ... )
    >>> for version in result:
    ...     print(version)
    {'a': {'smth': 49.0, 'msg': 'hi'}, 'base': {'msg': 'hi'}, 'b': ['hi']}
    {'a': {'smth': 2, 'msg': 'hi'}, 'base': {'msg': 'hi'}, 'b': ['hi']}
    """
    data = recursive_apply(data, partial(do_from, context=data))
    data = recursive_apply(data, partial(do_eval, locals=data))
    data = recursive_apply(data, do_each)

    data = list(data) if isinstance(data, Versions) else [data]
    data = [
        recursive_apply(item, partial(do_ref, context=item)) for item in data
    ]
    return data
