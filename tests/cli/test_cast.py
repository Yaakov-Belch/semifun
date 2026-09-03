"""Tests for CommandCall.cast_basic_types — signature-aware type casting."""

import pytest

from semifun.cli.CommandCall import CommandCall


def cast_args(fn, args, kwargs):
    """Backward-compatible helper: cast via CommandCall."""
    cc = CommandCall(args=tuple(args), kwargs=kwargs).with_fn(fn).cast_basic_types()
    return cc.args, dict(cc.kwargs)


# --- Basic type casting ---

def test_no_annotations():
    def fn(a, b):
        pass
    args, kwargs = cast_args(fn, ['hello', 'world'], {})
    assert args == ('hello', 'world')
    assert kwargs == {}


def test_int_casting():
    def fn(a: int, b: int):
        pass
    args, kwargs = cast_args(fn, ['3', '7'], {})
    assert args == (3, 7)


def test_float_casting():
    def fn(x: float):
        pass
    args, kwargs = cast_args(fn, ['3.14'], {})
    assert args == (3.14,)


def test_bool_casting():
    def fn(flag: bool):
        pass
    args, _ = cast_args(fn, ['true'], {})
    assert args == (True,)
    args, _ = cast_args(fn, ['0'], {})
    assert args == (False,)


def test_bool_invalid():
    def fn(flag: bool):
        pass
    with pytest.raises(ValueError, match="Cannot cast"):
        cast_args(fn, ['maybe'], {})


def test_str_passes_through():
    def fn(name: str):
        pass
    args, _ = cast_args(fn, ['Alice'], {})
    assert args == ('Alice',)


def test_unknown_type_passes_through():
    def fn(x: list):
        pass
    args, _ = cast_args(fn, ['[1,2,3]'], {})
    assert args == ('[1,2,3]',)


# --- Keyword args ---

def test_kwargs_casting():
    def fn(name: str, age: int):
        pass
    _, kwargs = cast_args(fn, [], {'name': 'Alice', 'age': '30'})
    assert kwargs == {'name': 'Alice', 'age': 30}


def test_mixed_positional_and_kwargs():
    def fn(greeting: str, name: str, times: int):
        pass
    args, kwargs = cast_args(fn, ['hello'], {'name': 'Bob', 'times': '3'})
    assert args == ('hello',)
    assert kwargs == {'name': 'Bob', 'times': 3}


# --- Variadic args ---

def test_var_positional_annotation():
    """*args:int casts each element."""
    def fn(label: str, *values: int):
        pass
    args, _ = cast_args(fn, ['total', '1', '2', '3'], {})
    assert args == ('total', 1, 2, 3)


def test_var_keyword_annotation():
    """**kwargs:bool casts each element."""
    def fn(**flags: bool):
        pass
    _, kwargs = cast_args(fn, [], {'verbose': 'true', 'dry_run': '0'})
    assert kwargs == {'verbose': True, 'dry_run': False}


def test_var_positional_no_annotation():
    """*args without annotation passes through."""
    def fn(*values):
        pass
    args, _ = cast_args(fn, ['a', 'b', 'c'], {})
    assert args == ('a', 'b', 'c')


def test_var_keyword_no_annotation():
    """**kwargs without annotation passes through."""
    def fn(**opts):
        pass
    _, kwargs = cast_args(fn, [], {'x': '1', 'y': '2'})
    assert kwargs == {'x': '1', 'y': '2'}


# --- Keyword-only params ---

def test_keyword_only_casting():
    def fn(a: str, *, port: int, host: str):
        pass
    args, kwargs = cast_args(fn, ['run'], {'port': '8080', 'host': 'localhost'})
    assert args == ('run',)
    assert kwargs == {'port': 8080, 'host': 'localhost'}


# --- Mixed variadic and named ---

def test_var_positional_with_named_kwargs():
    """Named kwargs match declared params; extras go to **kwargs."""
    def fn(label: str, *values: int, verbose: bool, **extra: float):
        pass
    args, kwargs = cast_args(fn, ['sum', '1', '2'], {'verbose': 'true', 'scale': '0.5'})
    assert args == ('sum', 1, 2)
    assert kwargs == {'verbose': True, 'scale': 0.5}
