"""Tests for CommandCall.split_kv_args — pure string parsing."""

from semifun.cli.CommandCall import CommandCall


def _split(tokens):
    """Split tokens into (args, kwargs) via CommandCall."""
    cc = CommandCall(cmd=None, fn=None, args=tuple(tokens), kwargs={}).split_kv_args()
    return list(cc.args), dict(cc.kwargs)


def test_empty():
    assert _split([]) == ([], {})


def test_positional_only():
    assert _split(['hello', 'world']) == (['hello', 'world'], {})


def test_kwargs_only():
    assert _split(['name=Alice', 'age=30']) == ([], {'name': 'Alice', 'age': '30'})


def test_interleaved():
    args, kwargs = _split(['hello', 'time=now', 'world', 'age=10'])
    assert args == ['hello', 'world']
    assert kwargs == {'time': 'now', 'age': '10'}


def test_equals_in_value():
    """Only the first '=' splits — value can contain '='."""
    args, kwargs = _split(['query=a=b=c'])
    assert args == []
    assert kwargs == {'query': 'a=b=c'}


def test_single_positional():
    assert _split(['run']) == (['run'], {})


def test_single_kwarg():
    assert _split(['port=8080']) == ([], {'port': '8080'})


def test_from_argv():
    """from_argv extracts cmd and keeps the rest as args."""
    cc = CommandCall.from_argv(['greet', 'name=Alice', 'world'])
    assert cc.cmd == 'greet'
    assert cc.args == ('name=Alice', 'world')
    assert cc.kwargs == {}


def test_from_argv_then_split():
    """from_argv + split_kv_args extracts cmd, then splits kv args."""
    cc = CommandCall.from_argv(['greet', 'name=Alice', 'world']).split_kv_args()
    assert cc.cmd == 'greet'
    assert cc.args == ('world',)
    assert cc.kwargs == {'name': 'Alice'}


def test_from_argv_empty():
    cc = CommandCall.from_argv([])
    assert cc.cmd is None
    assert cc.args == ()


def test_add_kwargs():
    cc = CommandCall(cmd=None, fn=None, args=('a',), kwargs={'x': '1'}).add_kwargs({'y': '2'})
    assert cc.kwargs == {'x': '1', 'y': '2'}


def test_add_kwargs_empty():
    cc = CommandCall(cmd=None, fn=None, args=('a',), kwargs={'x': '1'})
    assert cc.add_kwargs({}) is cc
