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

type CliMainFunction = callable

def semifun_cli():
    asyncio.run(cli_dispatch_engine(
        feature_type='cli',
        argv=sys.argv[1:],
        extra_kwargs=None,
        seed_data={CliMainFunction:True}, # Will be replaced.
        help_output=print,
    ))

async def cli_dispatch_engine(
    feature_type: str,
    argv: list[str],
    extra_kwargs: dict | None,
    seed_data: dict,
    help_output: callable,
):
    """Discover and run a CLI command with DI and type-cast arguments.

    Runs inside the caller's event loop — it does not create one.

    Args:
        feature_type: Feature type for CLI commands (e.g., 'cli').
        argv: Command-line arguments, without the program name.
        extra_kwargs: Pre-split keyword arguments merged into those parsed from
            argv.  `None` when there are none.
        seed_data: seed_data dict for DI; `{}` when there is none.
        help_output: callable for printing help text (e.g. `print`).

    When `seed_data` contains the key `CliMainFunction`, the value will be set.
    """
    cli_map = get_cached_feature_map(feature_type=feature_type)

    # --- Help handling ---

    if not argv or argv[0] == '--help':
        _print_help(cli_map, help_output)
        return

    command_name = argv[0]
    command_argv = argv[1:]

    fn = cli_map(feature=command_name, default=None)

    if fn is None:
        help_output(f"Unknown command: {command_name}\n")
        _print_help(cli_map, help_output)
        return

    if command_argv == ['--help']:
        _print_command_help(command_name, fn, help_output)
        return

    # --- Command execution ---

    if CliMainFunction in seed_data:
        seed_data = {**seed_data, CliMainFunction: fn}

    str_args, str_kwargs = split_argv(command_argv)
    if extra_kwargs:
        str_kwargs.update(extra_kwargs)
    cast_positional, cast_kwargs = cast_args(fn, str_args, str_kwargs)

    # testing seam: when feature_type is callable, it serves as the injectors map too
    injector_type = feature_type if callable(feature_type) else feature_type + '_inject'
    di = get_injector(injector_type).with_seed_data(seed_data)

    async def combined_context(*, ctx: Inject[AsyncExecutionContext]):
        try:
            await ctx.invoke_call_with_args(fn, args=cast_positional, kwargs=cast_kwargs)
        finally:
            if post_cli_hook := di.injectors_map(feature='post_cli_hook', default=None):
                await ctx.invoke_call_with_args(post_cli_hook, args=(), kwargs={})

    await di.async_call_with_args(fn=combined_context, args=(), kwargs={})

def _print_help(cli_map, help_output: callable):
    """Print help for all discovered CLI commands."""
    if not cli_map.feature_names:
        help_output("No commands available.")
        return
    help_output("Available commands:\n")
    for name, fn in cli_map.feature_names_and_objects:
        _print_command_help(name, fn, help_output)

def _print_command_help(name: str, fn, help_output: callable):
    """Print detailed help for a single command."""
    sig = signature_without_Inject(fn)
    doc = inspect.cleandoc(fn.__doc__ or "(no description)")
    indented = textwrap.indent(doc, "    ")
    help_output(f"{name}{sig}\n{indented}\n")

