from collections.abc import Mapping

from typing import Union, Any


def get_item_from_path(data: Union[dict, list], path: str) -> Any:
    """
    Access dict or list using a path split by '.'
    """
    for key in path.split("."):
        data = data[key]
    return data


def update_nested_dict(data, to_update):
    for key, value in to_update.items():
        if isinstance(data, Mapping):
            if isinstance(value, Mapping):
                data[key] = update_nested_dict(data.get(key, {}), value)
            else:
                data[key] = to_update[key]
        else:
            data = {key: to_update[key]}
    return data
