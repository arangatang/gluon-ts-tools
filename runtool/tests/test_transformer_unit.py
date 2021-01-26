from runtool.transformer import (
    recursive_apply,
    recursive_apply_dict,
    recursive_apply_list,
    apply_from,
    apply_ref,
    apply_eval,
    apply_each,
    apply_trial,
    evaluate,
    recurse_eval,
)

from runtool.datatypes import Versions


def transform(node: dict):
    """
    Converts node to a version object if the node has a key "versions"
    else it multiplies the node by 2 if the node has key "double"
    """
    if "version" in node:
        return Versions(node["version"])
    elif "double" in node:
        return 2 * node["double"]
    return node


def compare_recursive_apply(node, expected, fn=transform):
    assert recursive_apply(node, fn) == expected


def compare_apply_from(node, data, expected):
    assert apply_from(node, data) == expected


def compare_apply_ref(node, context, expected):
    assert apply_ref(node, context) == expected


def compare_apply_trial(text, locals, expected):
    assert apply_trial(text, locals) == expected


def compare_apply_each(node, expected):
    assert apply_each(node) == expected


def test_recursive_apply_double_simple():
    compare_recursive_apply(
        node={"double": 1},
        expected=2,
    )


def test_recursive_apply_double_nested():
    compare_recursive_apply(
        node={
            "no_double": 2,
            "double_this": {"double": 2},
        },
        expected={"no_double": 2, "double_this": 4},
    )


def test_recursive_apply_versions():
    compare_recursive_apply(
        node={
            "my_list": [
                {"hello": "there"},
                {"a": {"version": [1, 2]}},
            ]
        },
        expected=Versions(
            [
                {"my_list": [{"hello": "there"}, {"a": 1}]},
                {"my_list": [{"hello": "there"}, {"a": 2}]},
            ]
        ),
    )


def test_recursive_apply_trivial():
    compare_recursive_apply({}, {})


def test_recursive_apply_merging_versions_simple():
    compare_recursive_apply(
        node=[Versions([1, 2])],
        expected=Versions([[1], [2]]),
        fn=lambda x: x,
    )


def test_recursive_apply_merging_versions_list():
    compare_recursive_apply(
        node=[Versions([1, 2]), Versions([3, 4])],
        expected=Versions([[1, 3], [1, 4], [2, 3], [2, 4]]),
        fn=lambda x: x,
    )


def test_recursive_apply_merging_versions_dict():
    compare_recursive_apply(
        node={"a": Versions([1, 2]), "b": Versions([3, 4])},
        expected=Versions(
            [
                {"a": 1, "b": 3},
                {"a": 1, "b": 4},
                {"a": 2, "b": 3},
                {"a": 2, "b": 4},
            ]
        ),
        fn=lambda x: x,
    )


def test_recursive_apply_merging_versions_list_in_dict():
    compare_recursive_apply(
        node={
            "a": [Versions([1, 2]), Versions([3, 4])],
            "b": [Versions([5, 6]), Versions([7, 8])],
        },
        expected=Versions(
            [
                {"a": [1, 3], "b": [5, 7]},
                {"a": [1, 3], "b": [5, 8]},
                {"a": [1, 3], "b": [6, 7]},
                {"a": [1, 3], "b": [6, 8]},
                {"a": [1, 4], "b": [5, 7]},
                {"a": [1, 4], "b": [5, 8]},
                {"a": [1, 4], "b": [6, 7]},
                {"a": [1, 4], "b": [6, 8]},
                {"a": [2, 3], "b": [5, 7]},
                {"a": [2, 3], "b": [5, 8]},
                {"a": [2, 3], "b": [6, 7]},
                {"a": [2, 3], "b": [6, 8]},
                {"a": [2, 4], "b": [5, 7]},
                {"a": [2, 4], "b": [5, 8]},
                {"a": [2, 4], "b": [6, 7]},
                {"a": [2, 4], "b": [6, 8]},
            ]
        ),
        fn=lambda x: x,
    )


def test_recursive_apply_merging_versions_list_in_list():
    compare_recursive_apply(
        node=[
            [Versions([1, 2]), Versions([3, 4])],
            [Versions([5, 6]), Versions([7, 8])],
        ],
        expected=Versions(
            [
                [[1, 3], [5, 7]],
                [[1, 3], [5, 8]],
                [[1, 3], [6, 7]],
                [[1, 3], [6, 8]],
                [[1, 4], [5, 7]],
                [[1, 4], [5, 8]],
                [[1, 4], [6, 7]],
                [[1, 4], [6, 8]],
                [[2, 3], [5, 7]],
                [[2, 3], [5, 8]],
                [[2, 3], [6, 7]],
                [[2, 3], [6, 8]],
                [[2, 4], [5, 7]],
                [[2, 4], [5, 8]],
                [[2, 4], [6, 7]],
                [[2, 4], [6, 8]],
            ]
        ),
        fn=lambda x: x,
    )


def test_recursive_apply_merging_versions_dict_in_dict():
    compare_recursive_apply(
        node={"a": {"b": Versions([1, 2])}, "c": Versions([2, 3])},
        expected=Versions(
            [
                {"a": {"b": 1}, "c": 2},
                {"a": {"b": 1}, "c": 3},
                {"a": {"b": 2}, "c": 2},
                {"a": {"b": 2}, "c": 3},
            ]
        ),
        fn=lambda x: x,
    )


def test_recursive_apply_merging_versions_with_function():
    compare_recursive_apply(
        node={
            "my_list": [
                {"hello": "there"},
                {"a": {"version": [1, 2]}},
                {"b": {"version": [3, 4]}},
            ]
        },
        expected=Versions(
            [
                {"my_list": [{"hello": "there"}, {"a": 1}, {"b": 3}]},
                {"my_list": [{"hello": "there"}, {"a": 1}, {"b": 4}]},
                {"my_list": [{"hello": "there"}, {"a": 2}, {"b": 3}]},
                {"my_list": [{"hello": "there"}, {"a": 2}, {"b": 4}]},
            ]
        ),
    )


def test_apply_from_simple():
    compare_apply_from(
        node={
            "$from": "b",
            "some_key": "some_value",
        },
        data={
            "b": {
                "a": {"hello": "world"},
            },
        },
        expected={
            "a": {"hello": "world"},
            "some_key": "some_value",
        },
    )


def test_apply_from_empty():
    compare_apply_from(
        node={
            "$from": "b",
            "some_key": "some_value",
        },
        data={
            "b": {},
        },
        expected={
            "some_key": "some_value",
        },
    )


def test_apply_from_with_path():
    compare_apply_from(
        node={
            "$from": "b.c.0",
            "some_key": "some_value",
        },
        data={
            "b": {
                "c": [{"hello": "world"}],
            },
        },
        expected={
            "hello": "world",
            "some_key": "some_value",
        },
    )


def test_apply_ref_simple():
    compare_apply_ref(
        node={"$ref": "a"},
        context={"target": 1, "a": "hello"},
        expected="hello",
    )


def test_apply_ref_nested():
    compare_apply_ref(
        node={"$ref": "a.0.b"},
        context={
            "target": 1,
            "a": [{"b": {"$ref": "target"}}, "ignored"],
        },
        expected=1,
    )


def test_evaluate():
    assert (
        evaluate(
            text="2 + 2",
            locals={},
        )
        == 4
    )


def test_evaluate_with_mathlib_and_locals():
    assert (
        evaluate(
            text="len(uid) + pow(some_value, 2)",
            locals={"some_value": 2},
        )
        == 16
    )


def test_recurse_eval():
    def simple_eval(node, context):
        return eval(node["$eval"]) if "$eval" in node else node

    assert (
        recurse_eval(
            path="a.b.0.split(' ')",
            data={"a": {"b": [{"$eval": "'hey ' * 2"}]}},
            fn=simple_eval,
        )
        == ("a.b.0", "hey hey ")
    )


def compare_apply_eval(text, locals, expected):
    assert apply_eval(text, locals) == expected


def test_apply_eval_simple():
    compare_apply_eval(
        text={"$eval": "2 + 2"},
        locals={},
        expected=4,
    )


def test_apply_eval_referencing_locals():
    compare_apply_eval(
        text={"$eval": "2 + 5 * $.value"},
        locals={"value": 2},
        expected=12,
    )


def test_apply_eval_with_trial():
    compare_apply_eval(
        text={"$eval": "$trial.algorithm.some_value * 2"},
        locals={},
        expected={"$eval": "__trial__.algorithm.some_value * 2"},
    )


def test_apply_eval_with_trial_and_dollar():
    compare_apply_eval(
        text={"$eval": "$trial.algorithm.some_value * $.some_value"},
        locals={"some_value": 2},
        expected={"$eval": "__trial__.algorithm.some_value * 2"},
    )


def test_apply_trial_simple():
    compare_apply_trial(
        text={"$eval": "2 + __trial__.something[0]"},
        locals={"__trial__": {"something": [1, 2, 3]}},
        expected=3,
    )


def test_apply_each_simple():
    compare_apply_each(
        node={"$each": [1, 2, 3]},
        expected=Versions([1, 2, 3]),
    )


def test_apply_each_with_none():
    compare_apply_each(
        node={
            "c": "dummy",
            "$each": [
                "$None",
                {"a": 150, "b": 64},
            ],
        },
        expected=Versions(
            [
                {"c": "dummy"},
                {"a": 150, "b": 64, "c": "dummy"},
            ]
        ),
    )
