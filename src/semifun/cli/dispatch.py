"""CLI dispatch: discover a function by name, call it with DI and type-cast args.

This module composes the pieces (argv splitting, type casting, DI invocation)
into a complete CLI dispatcher.
"""

import asyncio
import sys

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
        reply=print,
    ))

async def cli_dispatch_engine(
    *,
    app: SemifunApp,
    ftype: str,
    argv: list[str],
    extra_kwargs: dict | None,
    seed_data: dict,
    parent_scope,
    reply: callable,
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
        reply: callable for output text (e.g. `print`).

    """

    cmd_call = CommandCall.from_argv(argv)
    cmd_call = cmd_call.with_fn(app.lookup_fn(ftype=ftype, fname=cmd_call.cmd, strict=False))

    if cmd_call.help_shown(app=app, ftype=ftype, reply=reply):
        return

    # --- Command execution ---

    cmd_call = (cmd_call
                .split_kv_args()
                .add_kwargs(extra_kwargs or {})
                .cast_basic_types())

    async with app.open_async_scope(parent_scope=parent_scope, seed_data=seed_data, ftype=ftype) as scope:
        await scope.fn_call(fn=cmd_call.fn, args=cmd_call.args, kwargs=cmd_call.kwargs)
