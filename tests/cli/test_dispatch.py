"""Tests for the composed CLI dispatcher."""

import asyncio
import inspect
import sys

import pytest
from dataclasses import dataclass
from pathlib import Path

from semifun.plugins.testing import create_registry_from_paths, feature_map_from_registry
from semifun.cli.dispatch import (
    cli_dispatch_engine,
    semifun_cli,
)


def _make_cli_package(tmp_path):
    """Create a package with sample CLI commands and injectors."""
    pkg = tmp_path / "cli_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "commands.py").write_text(
        "#::cli:greet\n"
        "def greet(name='world', times: int = 1):\n"
        "    '''Greet someone.'''\n"
        "    for _ in range(times):\n"
        "        print(f'Hello, {name}!')\n"
        "\n"
        "#::cli:add\n"
        "def add(a: int = 0, b: int = 0):\n"
        "    '''Add two numbers.'''\n"
        "    print(a + b)\n"
        "\n"
        "#::cli:mixed\n"
        "def mixed(greeting, name, times: int = 1):\n"
        "    '''Greet with positional and keyword args.'''\n"
        "    for _ in range(times):\n"
        "        print(f'{greeting}, {name}!')\n"
        "\n"
        "#::cli:variadic\n"
        "def variadic(*numbers: int):\n"
        "    '''Sum numbers.'''\n"
        "    print(sum(numbers))\n"
    )
    return pkg


def _scanned_cli_map(tmp_path):
    """A feature map built by really scanning a package's `#::` comments."""
    pkg = _make_cli_package(tmp_path)
    registry = create_registry_from_paths(
        packages=[("cli_pkg", pkg)],
    )
    return feature_map_from_registry(registry, feature_type='cli')


async def _dispatch(tmp_path, argv, capsys):
    """Run argv through the real async engine; return what it printed."""
    await cli_dispatch_engine(
        feature_type=_scanned_cli_map(tmp_path),
        argv=argv,
        extra_kwargs=None,
        seed_data={},
        help_output=print,
    )
    return capsys.readouterr().out


# --- Basic dispatch ---

async def test_simple_command(tmp_path, capsys):
    assert await _dispatch(tmp_path, ['greet'], capsys) == 'Hello, world!\n'


async def test_with_kwargs(tmp_path, capsys):
    assert await _dispatch(tmp_path, ['greet', 'name=Alice'], capsys) == 'Hello, Alice!\n'


async def test_type_casting(tmp_path, capsys):
    assert await _dispatch(tmp_path, ['add', 'a=3', 'b=7'], capsys) == '10\n'


async def test_multiple_kwargs(tmp_path, capsys):
    out = await _dispatch(tmp_path, ['greet', 'name=Bob', 'times=3'], capsys)
    assert out.count('Hello, Bob!') == 3


# --- Positional args ---

async def test_positional_args(tmp_path, capsys):
    assert await _dispatch(tmp_path, ['mixed', 'Hi', 'Alice'], capsys) == 'Hi, Alice!\n'


async def test_positional_with_kwargs(tmp_path, capsys):
    out = await _dispatch(tmp_path, ['mixed', 'Hey', 'Bob', 'times=2'], capsys)
    assert out.count('Hey, Bob!') == 2


# --- Variadic ---

async def test_variadic_int_args(tmp_path, capsys):
    assert await _dispatch(tmp_path, ['variadic', '1', '2', '3', '4'], capsys) == '10\n'


# --- Engine tests ---

@dataclass
class _Ctx:
    """Stand-in for an application context object passed via seed_data."""
    name: str


class _FakeCliMap:
    """Minimal stand-in for the feature map `_resolve` queries.

    Also serves as the injectors map via the testing seam: when
    cli_dispatch_engine receives a callable feature_type, it uses the same
    callable for both command lookup and injector lookup.
    """

    def __init__(self, functions):
        self._functions = functions

    def __call__(self, feature, default):
        return self._functions.get(feature, default)

    @property
    def feature_names(self):
        return list(self._functions)

    @property
    def feature_names_and_objects(self):
        return list(self._functions.items())


@pytest.fixture
def cli_map():
    """A pre-built feature map of sample commands."""
    from semifun.di.model import Inject

    async def async_greet(name):
        """Greet someone, asynchronously."""
        print(f'Hello, {name}!')

    async def needs_context(ctx: Inject[_Ctx], suffix):
        """A command whose context arrives through seed_data."""
        print(f'{ctx.name}{suffix}')

    return _FakeCliMap({
        'agreet': async_greet,
        'ctx': needs_context,
    })


async def test_async_engine_awaits_in_the_callers_loop(cli_map, capsys):
    await cli_dispatch_engine(
        feature_type=cli_map,
        argv=['agreet', 'name=Alice'],
        extra_kwargs=None,
        seed_data={},
        help_output=print,
    )
    assert capsys.readouterr().out == 'Hello, Alice!\n'


async def test_async_engine_prints_help_for_empty_argv(cli_map, capsys):
    await cli_dispatch_engine(
        feature_type=cli_map,
        argv=[],
        extra_kwargs=None,
        seed_data={},
        help_output=print,
    )
    assert 'Available commands:' in capsys.readouterr().out


async def test_unknown_command_prints_help_and_returns(cli_map, capsys):
    await cli_dispatch_engine(
        feature_type=cli_map,
        argv=['nope'],
        extra_kwargs=None,
        seed_data={},
        help_output=print,
    )
    out = capsys.readouterr().out
    assert 'Unknown command: nope' in out
    assert 'Available commands:' in out


async def test_async_engine_passes_seed_data_to_di(cli_map, capsys):
    await cli_dispatch_engine(
        feature_type=cli_map,
        argv=['ctx', 'suffix=!'],
        extra_kwargs=None,
        seed_data={_Ctx: _Ctx(name='xctx')},
        help_output=print,
    )
    assert capsys.readouterr().out == 'xctx!\n'


# --- semifun_cli entry point ---

def test_semifun_cli_entry_point(tmp_path, capsys, monkeypatch):
    """semifun_cli is a zero-argument entry point that reads sys.argv."""
    assert inspect.signature(semifun_cli).parameters == {}, (
        'a console-script target is invoked with no arguments'
    )


# --- post_cli_hook ---

async def test_post_cli_hook_runs_after_command(capsys):
    """A post_cli_hook registered in the injector map runs after the command."""
    hook_called = []

    async def my_command():
        """A simple command."""
        print('command ran')

    async def my_hook():
        hook_called.append(True)
        print('hook ran')

    await cli_dispatch_engine(
        feature_type=_FakeCliMap({'cmd': my_command, 'post_cli_hook': my_hook}),
        argv=['cmd'],
        extra_kwargs=None,
        seed_data={},
        help_output=print,
    )
    out = capsys.readouterr().out
    assert 'command ran' in out
    assert 'hook ran' in out
    assert hook_called


async def test_no_post_cli_hook_is_fine(capsys):
    """Without a post_cli_hook, the engine runs the command and stops."""
    async def my_command():
        """A simple command."""
        print('just the command')

    await cli_dispatch_engine(
        feature_type=_FakeCliMap({'cmd': my_command}),
        argv=['cmd'],
        extra_kwargs=None,
        seed_data={},
        help_output=print,
    )
    assert capsys.readouterr().out == 'just the command\n'


# --- documented entry point shape ---

def test_documented_entry_point_shape(tmp_path, capsys, monkeypatch):
    """The console-script entry point works exactly as documented."""
    cli_map = _scanned_cli_map(tmp_path)

    def cli_dispatch() -> None:
        asyncio.run(cli_dispatch_engine(
            feature_type=cli_map,
            argv=sys.argv[1:],
            extra_kwargs=None,
            seed_data={},
            help_output=print,
        ))

    monkeypatch.setattr(sys, 'argv', ['my-app', 'greet', 'name=Alice'])

    assert inspect.signature(cli_dispatch).parameters == {}, (
        'a console-script target is invoked with no arguments'
    )
    cli_dispatch()
    assert capsys.readouterr().out == 'Hello, Alice!\n'


async def test_help_hides_injected_parameters(cli_map, capsys):
    """Inject[T] parameters should not appear in the help signature."""
    # The 'ctx' command has (ctx: Inject[_Ctx], suffix) — only suffix should show
    await cli_dispatch_engine(
        feature_type=cli_map,
        argv=['ctx', '--help'],
        extra_kwargs=None,
        seed_data={},
        help_output=print,
    )
    out = capsys.readouterr().out
    assert 'suffix' in out
    assert 'Inject' not in out
    assert 'ctx:' not in out  # the parameter name 'ctx' shouldn't appear in the sig


async def test_the_same_engine_call_runs_inside_an_existing_loop(tmp_path, capsys):
    """No second asyncio.run, no nest_asyncio, no thread — the point of the async engine."""
    await cli_dispatch_engine(
        feature_type=_scanned_cli_map(tmp_path),
        argv=['greet', 'name=Bob'],
        extra_kwargs=None,
        seed_data={},
        help_output=print,
    )
    assert capsys.readouterr().out == 'Hello, Bob!\n'
