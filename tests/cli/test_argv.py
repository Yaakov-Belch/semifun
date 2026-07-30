"""Tests for split_argv — pure string parsing."""

from yb_tools.cli.argv import split_argv


def test_empty():
    assert split_argv([]) == ([], {})


def test_positional_only():
    assert split_argv(['hello', 'world']) == (['hello', 'world'], {})


def test_kwargs_only():
    assert split_argv(['name=Alice', 'age=30']) == ([], {'name': 'Alice', 'age': '30'})


def test_interleaved():
    args, kwargs = split_argv(['hello', 'time=now', 'world', 'age=10'])
    assert args == ['hello', 'world']
    assert kwargs == {'time': 'now', 'age': '10'}


def test_equals_in_value():
    """Only the first '=' splits — value can contain '='."""
    args, kwargs = split_argv(['query=a=b=c'])
    assert args == []
    assert kwargs == {'query': 'a=b=c'}


def test_single_positional():
    assert split_argv(['run']) == (['run'], {})


def test_single_kwarg():
    assert split_argv(['port=8080']) == ([], {'port': '8080'})
