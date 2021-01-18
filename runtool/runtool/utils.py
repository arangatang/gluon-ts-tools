from typing import Union, Any


def get_item_from_path(data: Union[dict, list], path: str) -> Any:
    """
    Access dict or list using a path split by '.'

    Example:
    data = {
        "hello": [1, 2, 3, {"there": "world"}]
    }
    path = "hello.3.there"

    results in the value "world" being returned.
    """
    for key in path.split("."):
        try:
            data = data[key]
        except TypeError:
            data = data[int(key)]
    return data


def update_nested_dict(data: dict, to_update: dict) -> dict:
    """
    Returns an updated version of the `data` dict updated with any changes from the `to_update` dict.
    This behaves differently from the `dict.update` method, see the example below.

    Example.
    data = {"root": {"smth": 10, "smth_else": 20}}
    to_update = {"root": {"smth": {"hello" : "world"}}}

    after running this function with these parameters, the following is returned.
    {'root': {'smth': {'hello': 'world'}, 'smth_else': 20}}

    If one would instead run `data.update(to_update)` the result would have been the following:
    {'root': {'smth': {'hello': 'world'}}}
    """
    for key, value in to_update.items():
        if isinstance(data, dict):
            if isinstance(value, dict):
                data[key] = update_nested_dict(data.get(key, {}), value)
            else:
                data[key] = to_update[key]
        else:
            data = {key: to_update[key]}
    return data
