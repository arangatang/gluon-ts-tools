from functools import partial

from runtool.recurse_config import recursive_apply
from runtool.transformations import do_each, do_eval, do_from, do_ref, do_trial
from runtool.datatypes import Versions


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

    Parameters
    ----------
    data
        The dictionary which should be transformed
    Returns
    -------
    list
        the transformed `data` where each item is a version of the data.
    """
    data = recursive_apply(data, partial(do_from, context=data))
    data = recursive_apply(data, partial(do_eval, locals=data))
    data = recursive_apply(data, do_each)

    data = list(data) if isinstance(data, Versions) else [data]
    data = [
        recursive_apply(item, partial(do_ref, context=item)) for item in data
    ]
    return data
