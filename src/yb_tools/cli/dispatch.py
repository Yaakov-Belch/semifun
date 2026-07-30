"""CLI dispatch: discover a function by name, call it with DI and type-cast args.

This module composes the pieces (argv splitting, type casting, DI invocation)
into a complete CLI dispatcher.

Two engines are exposed:

* `cli_dispatch_engine` — async, awaits in the caller's loop.  The standard.
* `sync_cli_dispatch_engine` — sync, for commands that must own the loop.
"""

import asyncio
import inspect
import sys
import textwrap

from yb_tools.plugins.registry import get_cached_feature_map

from yb_tools.di.registry_integration import get_injector

from .argv import split_argv
from .cast import cast_args


async def cli_dispatch_engine(
    cli_feature_type: str,
    injector_feature_type: str,
    argv: list[str],
    seed_data: dict,
):
    """Discover and run a CLI command with DI and type-cast arguments.

    Runs inside the caller's event loop — it does not create one.  This is
    the standard engine; see `sync_cli_dispatch_engine` for the other path.

    Args:
        cli_feature_type: Feature type for CLI commands (e.g., 'cli').
        injector_feature_type: Feature type for DI injectors (e.g., 'cli_inject').
        argv: Command-line arguments, without the program name.
        seed_data: seed_data dict for DI; `{}` when there is none.
    """
    resolved = _resolve(cli_feature_type, argv)
    if resolved is None:
        return
    fn, cast_positional, cast_kwargs = resolved

    di = get_injector(injector_feature_type).with_seed_data(seed_data)

    result = await di.async_call_with_args(
        fn=fn,
        args=cast_positional,
        kwargs=cast_kwargs,
    )

    if result is not None:
        print(result)


def sync_cli_dispatch_engine(
    cli_feature_type: str,
    injector_feature_type: str,
    argv: list[str],
    seed_data: dict,
):
    """Same as `cli_dispatch_engine`, but owns the event loop.

    Use this only when a command function is itself sync and
    starts its own loop (marked `@sync_function_owns_async_loop`); such a
    command cannot be awaited and so forces the dispatcher to be outermost.
    Prefer `cli_dispatch_engine`.
    """
    resolved = _resolve(cli_feature_type, argv)
    if resolved is None:
        return
    fn, cast_positional, cast_kwargs = resolved

    di = get_injector(injector_feature_type).with_seed_data(seed_data)

    if getattr(fn, 'sync_function_owns_async_loop', False):
        result = di.sync_call_with_args(
            fn=fn,
            args=cast_positional,
            kwargs=cast_kwargs,
        )
    else:
        result = asyncio.run(di.async_call_with_args(
            fn=fn,
            args=cast_positional,
            kwargs=cast_kwargs,
        ))

    if result is not None:
        print(result)


def _resolve(cli_feature_type: str, argv: list[str]):
    """Find the command and prepare its arguments — everything before the call.

    Returns (fn, args, kwargs), or None when help was printed instead.
    Exits with status 1 on an unknown command.
    """
    cli_map = get_cached_feature_map(feature_type=cli_feature_type)

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
    sig = inspect.signature(fn)
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
