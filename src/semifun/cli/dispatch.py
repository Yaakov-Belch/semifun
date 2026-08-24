"""CLI dispatch: discover a function by name, call it with DI and type-cast args.

This module composes the pieces (argv splitting, type casting, DI invocation)
into a complete CLI dispatcher.
"""

import asyncio
import inspect
import sys
import textwrap

from semifun.plugins.registry import get_cached_feature_map

from semifun.di.model import Inject, signature_without_Inject
from semifun.di.async_execution_context import AsyncExecutionContext
from semifun.di.registry_integration import get_injector

from .argv import split_argv
from .cast import cast_args

def semifun_cli():
    asyncio.run(cli_dispatch_engine(
        feature_type='cli',
        argv=sys.argv[1:],
        seed_data={},
    ))

async def cli_dispatch_engine(
    feature_type: str,
    argv: list[str],
    seed_data: dict,
    help_output: callable,
):
    """Discover and run a CLI command with DI and type-cast arguments.

    Runs inside the caller's event loop — it does not create one.

    Args:
        feature_type: Feature type for CLI commands (e.g., 'cli').
        argv: Command-line arguments, without the program name.
        seed_data: seed_data dict for DI; `{}` when there is none.
    """
    resolved = _resolve(feature_type, argv)
    if resolved is None:
        return
    fn, cast_positional, cast_kwargs = resolved

    di = _get_di(feature_type).with_seed_data(seed_data)

    async def combined_context(*, ctx: Inject[AsyncExecutionContext]):
        await ctx.invoke_call_with_args(fn, args=cast_positional, kwargs=cast_kwargs)

        if post_cli_hook := di.injectors_map(feature='post_cli_hook', default=None):
            await ctx.invoke_call_with_args(post_cli_hook, args=(), kwargs={})

    await di.async_call_with_args(fn=combined_context, args=(), kwargs={})



def _get_di(feature_type):
    # testing seam: when feature_type is callable, it serves as the injectors map too
    injector_type = feature_type if callable(feature_type) else feature_type + '_inject'
    return get_injector(injector_type)


def _resolve(feature_type: str, argv: list[str]):
    """Find the command and prepare its arguments — everything before the call.

    Returns (fn, args, kwargs), or None when help was printed instead.
    Exits with status 1 on an unknown command.
    """
    cli_map = get_cached_feature_map(feature_type=feature_type)

    if not argv or argv[0] == '--help':
        _print_help(cli_map)
        return None

    command_name = argv[0]
    command_argv = argv[1:]

    fn = cli_map(feature=command_name, default=None)

    if fn is None:
        print(f"Unknown command: {command_name}")
        print()
        _print_help(cli_map)
        sys.exit(1)

    if command_argv == ['--help']:
        _print_command_help(command_name, fn)
        return None

    str_args, str_kwargs = split_argv(command_argv)
    cast_positional, cast_kwargs = cast_args(fn, str_args, str_kwargs)
    return fn, cast_positional, cast_kwargs


def _print_command_help(name: str, fn):
    """Print detailed help for a single command."""
    sig = signature_without_Inject(fn)
    doc = inspect.cleandoc(fn.__doc__ or "(no description)")
    indented = textwrap.indent(doc, "    ")
    print(f"{name}{sig}")
    print(indented)


def _print_help(cli_map):
    """Print help for all discovered CLI commands."""
    if not cli_map.feature_names:
        print("No commands available.")
        return
    print("Available commands:\n")
    for name, fn in cli_map.feature_names_and_objects:
        _print_command_help(name, fn)
        print()
