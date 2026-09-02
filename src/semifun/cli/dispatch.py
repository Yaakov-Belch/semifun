"""CLI dispatch: discover a function by name, call it with DI and type-cast args.

This module composes the pieces (argv splitting, type casting, DI invocation)
into a complete CLI dispatcher.
"""

import asyncio
import inspect
import sys
import textwrap

from semifun.dispatch.Inject import signature_without_Inject
from semifun.dispatch.SemifunApp import SemifunApp, app as _default_app

from .argv import split_argv
from .cast import cast_args

def semifun_cli():
    asyncio.run(cli_dispatch_engine(
        app=_default_app,
        ftype='cli',
        argv=sys.argv[1:],
        extra_kwargs=None,
        seed_data={},
        parent_ctx=None,
        help_output=print,
    ))

async def cli_dispatch_engine(
    *,
    app: SemifunApp,
    ftype: str,
    argv: list[str],
    extra_kwargs: dict | None,
    seed_data: dict,
    parent_ctx,
    help_output: callable,
):
    """Discover and run a CLI command with DI and type-cast arguments.

    Args:
        app: SemifunApp instance (use _default_app for production).
        ftype: Feature type for CLI commands (e.g., 'cli').
        argv: Command-line arguments, without the program name.
        extra_kwargs: Pre-split keyword arguments merged into those parsed from
            argv.  `None` when there are none.
        seed_data: seed_data dict for DI; `{}` when there is none.
        parent_ctx: Parent DI context for inheriting cached values (e.g., cli_di_ctx).
        help_output: callable for printing help text (e.g. `print`).

    """
    fn_items = app.fn_items(ftype=ftype)

    # --- Help handling ---

    if not argv or argv[0] == '--help':
        _print_help(fn_items=fn_items, help_output=help_output)
        return

    command_name = argv[0]
    command_argv = argv[1:]

    fn = app.lookup_fn(ftype=ftype, fname=command_name, strict=False)

    if fn is None:
        help_output(f"Unknown command: {command_name}\n")
        _print_help(fn_items=fn_items, help_output=help_output)
        return

    if command_argv == ['--help']:
        _print_command_help(name=command_name, fn=fn, help_output=help_output)
        return

    # --- Command execution ---

    str_args, str_kwargs = split_argv(command_argv)
    if extra_kwargs:
        str_kwargs.update(extra_kwargs)
    cast_positional, cast_kwargs = cast_args(fn, str_args, str_kwargs)

    async with app.open_async_di_ctx(parent_ctx=parent_ctx, seed_data=seed_data, ftype=ftype) as ctx:
        await ctx.fn_call(fn=fn, args=cast_positional, kwargs=cast_kwargs)
        post_cli_hook = app.lookup_fn(ftype=ftype, fname='post_cli_hook', strict=False)
        if post_cli_hook:
            await ctx.fn_call(fn=post_cli_hook, args=(), kwargs={})

def _print_help(*, fn_items, help_output: callable):
    """Print help for all discovered CLI commands."""
    if not fn_items:
        help_output("No commands available.")
        return
    help_output("Available commands:\n")
    for name, fn in fn_items:
        _print_command_help(name=name, fn=fn, help_output=help_output)

def _print_command_help(*, name: str, fn, help_output: callable):
    """Print detailed help for a single command."""
    sig = signature_without_Inject(fn)
    doc = inspect.cleandoc(fn.__doc__ or "(no description)")
    indented = textwrap.indent(doc, "    ")
    help_output(f"{name}{sig}\n{indented}\n")
