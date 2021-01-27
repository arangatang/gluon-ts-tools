import itertools
import math
import re
import json
from functools import partial
from typing import Any, Callable, Tuple
from uuid import uuid4

from runtool.datatypes import DotDict, Versions
from runtool.utils import get_item_from_path, update_nested_dict
from runtool.recurse_config import recursive_apply


def apply_from(node: dict, data: dict) -> dict:
    """
    Update the node with the data which the path in node['$from'] is pointing to.
    i.e.

    >>> apply_from(
    ...     node = {"$from": "another_node.a_key", "some_key": "some_value"},
    ...     data = {"another_node": {"a_key": {"hello": "world"}}}
    ... )
    {'hello': 'world', 'some_key': 'some_value'}

    Parameters
    ----------
    node
        The node which should be processed.
    data:
        Data which can be referenced if $from is in node.
    Returns
    -------
    Dict
        the `node` updated with values from `data`
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

    Parameters
    ----------
    node
        The node which should be processed.
    context
        The data which can be referenced using $ref
    Returns
    -------
    Any
        The data which is referenced
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
    ...     text = "len(uid) + pow(some_value, 2)",
    ...     locals = {"some_value": 2}
    ... )
    16.0

    Parameters
    ----------
    text
        The text which should be evaluated
    locals
        The locals parameter to the `eval` function in the standard library.
    Returns
    -------
    Any
        The value after applying `eval` to the text.
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

    Parameters
    ----------
    path
        The path to fetch from in the data
    data
        Dictionary from which data should be fetched
    fn
        function to call with the fetched data as parameter
    Returns
    -------
    Tuple[str, Any]
        The path and the value after applying the `fn`
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

    Parameters
    ----------
    node
        The node which should be processed.
    locals:
        The local variables available for when calling eval.
    Returns
    -------
    Any
        The transformed node.
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

    Parameters
    ----------
    node
        The node which should be processed.
    locals:
        The local variables available for when calling eval.
    Returns
    -------
    Any
        The transformed node.
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
