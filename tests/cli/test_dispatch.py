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
    sync_cli_dispatch_engine,
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
        "\n"
        "from semifun.cli.decorator import sync_function_owns_async_loop\n"
        "\n"
        "#::cli:sync_server\n"
        "@sync_function_owns_async_loop\n"
        "def sync_server(host='localhost', port: int = 8080):\n"
        "    '''A sync function that would own the event loop.'''\n"
        "    print(f'{host}:{port}')\n"
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
        seed_data={},
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


# --- sync_function_owns_async_loop ---

def test_sync_server_dispatch(tmp_path, capsys):
    """A loop-owning command needs the sync engine; the async one cannot await it."""
    sync_cli_dispatch_engine(
        feature_type=_scanned_cli_map(tmp_path),
        argv=['sync_server', 'host=0.0.0.0', 'port=9090'],
        seed_data={},
    )
    assert capsys.readouterr().out == '0.0.0.0:9090\n'


# --- The two engines ---

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
    from semifun.cli.decorator import sync_function_owns_async_loop

    async def async_greet(name):
        """Greet someone, asynchronously."""
        print(f'Hello, {name}!')

    @sync_function_owns_async_loop
    def loop_owning(host, port: int):
        """A sync command that starts its own loop."""
        print(f'{host}:{port}')

    async def needs_context(ctx: Inject[_Ctx], suffix):
        """A command whose context arrives through seed_data."""
        print(f'{ctx.name}{suffix}')

    return _FakeCliMap({
        'agreet': async_greet,
        'serve': loop_owning,
        'ctx': needs_context,
    })


async def test_async_engine_awaits_in_the_callers_loop(cli_map, capsys):
    await cli_dispatch_engine(
        feature_type=cli_map,
        argv=['agreet', 'name=Alice'],
        seed_data={},
    )
    assert capsys.readouterr().out == 'Hello, Alice!\n'


async def test_async_engine_prints_help_for_empty_argv(cli_map, capsys):
    await cli_dispatch_engine(
        feature_type=cli_map,
        argv=[],
        seed_data={},
    )
    assert 'Available commands:' in capsys.readouterr().out


def test_sync_engine_runs_a_loop_owning_command(cli_map, capsys):
    sync_cli_dispatch_engine(
        feature_type=cli_map,
        argv=['serve', 'host=localhost', 'port=9090'],
        seed_data={},
    )
    assert capsys.readouterr().out == 'localhost:9090\n'


def test_sync_engine_runs_an_async_command(cli_map, capsys):
    sync_cli_dispatch_engine(
        feature_type=cli_map,
        argv=['agreet', 'name=Bob'],
        seed_data={},
    )
    assert capsys.readouterr().out == 'Hello, Bob!\n'


def test_unknown_command_exits_nonzero(cli_map, capsys):
    with pytest.raises(SystemExit) as exc:
        sync_cli_dispatch_engine(
            feature_type=cli_map,
            argv=['nope'],
            seed_data={},
        )
    assert exc.value.code == 1
    assert 'Unknown command: nope' in capsys.readouterr().out


async def test_async_engine_passes_seed_data_to_di(cli_map, capsys):
    await cli_dispatch_engine(
        feature_type=cli_map,
        argv=['ctx', 'suffix=!'],
        seed_data={_Ctx: _Ctx(name='xctx')},
    )
    assert capsys.readouterr().out == 'xctx!\n'


def test_sync_engine_passes_seed_data_to_di(cli_map, capsys):
    sync_cli_dispatch_engine(
        feature_type=cli_map,
        argv=['ctx', 'suffix=?'],
        seed_data={_Ctx: _Ctx(name='xctx')},
    )
    assert capsys.readouterr().out == 'xctx?\n'


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
        seed_data={},
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
        seed_data={},
    )
    assert capsys.readouterr().out == 'just the command\n'


def test_sync_post_cli_hook_runs_after_command(capsys):
    """post_cli_hook works with the sync engine too."""
    hook_called = []

    async def my_command():
        """A simple command."""
        print('command ran')

    async def my_hook():
        hook_called.append(True)
        print('hook ran')

    sync_cli_dispatch_engine(
        feature_type=_FakeCliMap({'cmd': my_command, 'post_cli_hook': my_hook}),
        argv=['cmd'],
        seed_data={},
    )
    out = capsys.readouterr().out
    assert 'command ran' in out
    assert 'hook ran' in out
    assert hook_called


# --- documented entry point shape ---

def test_documented_entry_point_shape(tmp_path, capsys, monkeypatch):
    """The console-script entry point works exactly as documented."""
    cli_map = _scanned_cli_map(tmp_path)

    def cli_dispatch() -> None:
        asyncio.run(cli_dispatch_engine(
            feature_type=cli_map,
            argv=sys.argv[1:],
            seed_data={},
        ))

    monkeypatch.setattr(sys, 'argv', ['my-app', 'greet', 'name=Alice'])

    assert inspect.signature(cli_dispatch).parameters == {}, (
        'a console-script target is invoked with no arguments'
    )
    cli_dispatch()
    assert capsys.readouterr().out == 'Hello, Alice!\n'


async def test_the_same_engine_call_runs_inside_an_existing_loop(tmp_path, capsys):
    """No second asyncio.run, no nest_asyncio, no thread — the point of the async engine."""
    await cli_dispatch_engine(
        feature_type=_scanned_cli_map(tmp_path),
        argv=['greet', 'name=Bob'],
        seed_data={},
    )
    assert capsys.readouterr().out == 'Hello, Bob!\n'
