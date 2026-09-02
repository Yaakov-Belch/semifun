"""Tests for the composed CLI dispatcher."""

import asyncio
import inspect
import sys

import pytest
from dataclasses import dataclass

from semifun.dispatch.Inject import Inject
from semifun.dispatch.SemifunApp import SemifunApp
from semifun.dispatch.load_lookup_tables import LoadedFn
from semifun.cli.dispatch import (
    cli_dispatch_engine,
    semifun_cli,
)


def _make_app(ftype, fns, inject_fns=None):
    """Build a test SemifunApp with the given functions."""
    tables = {ftype: {name: LoadedFn(fn=fn) for name, fn in fns.items()}}
    if inject_fns:
        tables[ftype + '_inject'] = {name: LoadedFn(fn=fn) for name, fn in inject_fns.items()}
    return SemifunApp(entry_points_group=tables)


# --- Simple CLI commands ---

def _simple_app():
    def greet(name='world', times: int = 1):
        '''Greet someone.'''
        for _ in range(times):
            print(f'Hello, {name}!')

    def add(a: int = 0, b: int = 0):
        '''Add two numbers.'''
        print(a + b)

    def mixed(greeting, name, times: int = 1):
        '''Greet with positional and keyword args.'''
        for _ in range(times):
            print(f'{greeting}, {name}!')

    def variadic(*numbers: int):
        '''Sum numbers.'''
        print(sum(numbers))

    return _make_app('cli', {
        'greet': greet, 'add': add, 'mixed': mixed, 'variadic': variadic,
    })


async def _dispatch(argv, capsys, app=None):
    """Run argv through the async engine; return what it printed."""
    if app is None:
        app = _simple_app()
    await cli_dispatch_engine(
        app=app,
        ftype='cli',
        argv=argv,
        extra_kwargs=None,
        seed_data={},
        parent_ctx=None,
        help_output=print,
    )
    return capsys.readouterr().out


# --- Basic dispatch ---

async def test_simple_command(capsys):
    assert await _dispatch(['greet'], capsys) == 'Hello, world!\n'


async def test_with_kwargs(capsys):
    assert await _dispatch(['greet', 'name=Alice'], capsys) == 'Hello, Alice!\n'


async def test_type_casting(capsys):
    assert await _dispatch(['add', 'a=3', 'b=7'], capsys) == '10\n'


async def test_multiple_kwargs(capsys):
    out = await _dispatch(['greet', 'name=Bob', 'times=3'], capsys)
    assert out.count('Hello, Bob!') == 3


# --- Positional args ---

async def test_positional_args(capsys):
    assert await _dispatch(['mixed', 'Hi', 'Alice'], capsys) == 'Hi, Alice!\n'


async def test_positional_with_kwargs(capsys):
    out = await _dispatch(['mixed', 'Hey', 'Bob', 'times=2'], capsys)
    assert out.count('Hey, Bob!') == 2


# --- Variadic ---

async def test_variadic_int_args(capsys):
    assert await _dispatch(['variadic', '1', '2', '3', '4'], capsys) == '10\n'


# --- Engine tests ---

@dataclass
class _Ctx:
    """Stand-in for an application context object passed via seed_data."""
    name: str


async def test_async_engine_awaits_in_the_callers_loop(capsys):
    async def async_greet(name):
        """Greet someone, asynchronously."""
        print(f'Hello, {name}!')

    app = _make_app('cli', {'agreet': async_greet})
    await cli_dispatch_engine(
        app=app,
        ftype='cli',
        argv=['agreet', 'name=Alice'],
        extra_kwargs=None,
        seed_data={},
        parent_ctx=None,
        help_output=print,
    )
    assert capsys.readouterr().out == 'Hello, Alice!\n'


async def test_async_engine_prints_help_for_empty_argv(capsys):
    async def async_greet(name):
        """Greet someone, asynchronously."""
        print(f'Hello, {name}!')

    app = _make_app('cli', {'agreet': async_greet})
    await cli_dispatch_engine(
        app=app,
        ftype='cli',
        argv=[],
        extra_kwargs=None,
        seed_data={},
        parent_ctx=None,
        help_output=print,
    )
    assert 'Available commands:' in capsys.readouterr().out


async def test_unknown_command_prints_help_and_returns(capsys):
    async def async_greet(name):
        """Greet someone, asynchronously."""
        print(f'Hello, {name}!')

    app = _make_app('cli', {'agreet': async_greet})
    await cli_dispatch_engine(
        app=app,
        ftype='cli',
        argv=['nope'],
        extra_kwargs=None,
        seed_data={},
        parent_ctx=None,
        help_output=print,
    )
    out = capsys.readouterr().out
    assert 'Unknown command: nope' in out
    assert 'Available commands:' in out


async def test_async_engine_passes_seed_data_to_di(capsys):
    async def needs_context(ctx: Inject[_Ctx], suffix):
        """A command whose context arrives through seed_data."""
        print(f'{ctx.name}{suffix}')

    app = _make_app('cli', {'ctx': needs_context})
    await cli_dispatch_engine(
        app=app,
        ftype='cli',
        argv=['ctx', 'suffix=!'],
        extra_kwargs=None,
        seed_data={_Ctx: _Ctx(name='xctx')},
        parent_ctx=None,
        help_output=print,
    )
    assert capsys.readouterr().out == 'xctx!\n'


# --- semifun_cli entry point ---

def test_semifun_cli_entry_point():
    """semifun_cli is a zero-argument entry point that reads sys.argv."""
    assert inspect.signature(semifun_cli).parameters == {}, (
        'a console-script target is invoked with no arguments'
    )


# --- post_cli_hook ---

async def test_post_cli_hook_runs_after_command(capsys):
    """A post_cli_hook registered in the feature map runs after the command."""
    hook_called = []

    async def my_command():
        """A simple command."""
        print('command ran')

    async def my_hook():
        hook_called.append(True)
        print('hook ran')

    app = _make_app('cli', {'cmd': my_command, 'post_cli_hook': my_hook})
    await cli_dispatch_engine(
        app=app,
        ftype='cli',
        argv=['cmd'],
        extra_kwargs=None,
        seed_data={},
        parent_ctx=None,
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

    app = _make_app('cli', {'cmd': my_command})
    await cli_dispatch_engine(
        app=app,
        ftype='cli',
        argv=['cmd'],
        extra_kwargs=None,
        seed_data={},
        parent_ctx=None,
        help_output=print,
    )
    assert capsys.readouterr().out == 'just the command\n'


# --- documented entry point shape ---

def test_documented_entry_point_shape(capsys, monkeypatch):
    """The console-script entry point works exactly as documented."""
    app = _simple_app()

    def cli_dispatch() -> None:
        asyncio.run(cli_dispatch_engine(
            app=app,
            ftype='cli',
            argv=sys.argv[1:],
            extra_kwargs=None,
            seed_data={},
            parent_ctx=None,
            help_output=print,
        ))

    monkeypatch.setattr(sys, 'argv', ['my-app', 'greet', 'name=Alice'])

    assert inspect.signature(cli_dispatch).parameters == {}, (
        'a console-script target is invoked with no arguments'
    )
    cli_dispatch()
    assert capsys.readouterr().out == 'Hello, Alice!\n'


async def test_help_hides_injected_parameters(capsys):
    """Inject[T] parameters should not appear in the help signature."""
    async def needs_context(ctx: Inject[_Ctx], suffix):
        """A command whose context arrives through seed_data."""
        print(f'{ctx.name}{suffix}')

    app = _make_app('cli', {'ctx': needs_context})
    await cli_dispatch_engine(
        app=app,
        ftype='cli',
        argv=['ctx', '--help'],
        extra_kwargs=None,
        seed_data={},
        parent_ctx=None,
        help_output=print,
    )
    out = capsys.readouterr().out
    assert 'suffix' in out
    assert 'Inject' not in out
    assert 'ctx:' not in out  # the parameter name 'ctx' shouldn't appear in the sig


async def test_the_same_engine_call_runs_inside_an_existing_loop(capsys):
    """No second asyncio.run, no nest_asyncio, no thread — the point of the async engine."""
    await _dispatch(['greet', 'name=Bob'], capsys)
    assert True  # if we got here without error, the engine ran in the caller's loop
