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

from .CommandCall import CommandCall

def semifun_cli():
    asyncio.run(cli_dispatch_engine(
        app=_default_app,
        ftype='cli',
        argv=sys.argv[1:],
        extra_kwargs=None,
        seed_data={},
        parent_scope=None,
        help_output=print,
    ))

async def cli_dispatch_engine(
    *,
    app: SemifunApp,
    ftype: str,
    argv: list[str],
    extra_kwargs: dict | None,
    seed_data: dict,
    parent_scope,
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
        parent_scope: Parent DI context for inheriting cached values (e.g., cli_scope).
        help_output: callable for printing help text (e.g. `print`).

    """

    # --- Help handling ---

    if not argv or argv[0] == '--help':
        _print_help(app=app, ftype=ftype, help_output=help_output)
        return

    cmd_call = CommandCall.from_argv(argv)

    fn = app.lookup_fn(ftype=ftype, fname=cmd_call.cmd, strict=False)

    if fn is None:
        help_output(f"Unknown command: {cmd_call.cmd}\n")
        _print_help(app=app, ftype=ftype, help_output=help_output)
        return

    if cmd_call.args == ('--help',):
        _print_command_help(name=cmd_call.cmd, fn=fn, help_output=help_output)
        return

    # --- Command execution ---

    cmd_call = (cmd_call
                .split_kv_args()
                .add_kwargs(extra_kwargs or {})
                .with_fn(fn)
                .cast_basic_types())

    async with app.open_async_scope(parent_scope=parent_scope, seed_data=seed_data, ftype=ftype) as scope:
        await scope.fn_call(fn=cmd_call.fn, args=cmd_call.args, kwargs=cmd_call.kwargs)

def _print_help(*, app, ftype, help_output: callable):
    """Print help for all discovered CLI commands."""
    fn_items = app.fn_items(ftype=ftype)
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
