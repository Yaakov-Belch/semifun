[[cli-dispatch:entry-point]]
# Using the engine as your CLI dispatcher: `asyncio.run()` at the entry point only

* The application owns the event loop; the engine only runs inside it.
* A `cli_dispatch` console script that is one direct `asyncio.run()`, wired via `[project.scripts]`.
* Everywhere else, await the engine directly — there is no wrapper to reuse.


`cli_dispatch_engine` is `async` on purpose — see
[[:cli-dispatch-engine-does-not-own-the-loop]].  The loop is started once, at
the process boundary, by the application.

```python
# my_app/cli.py — the console-script entry point

import asyncio
import sys

from semifun_cli_dispatch.dispatch import cli_dispatch_engine


def cli_dispatch() -> None:
    """Entry point: start the event loop and hand over to the engine."""
    asyncio.run(cli_dispatch_engine(
        cli_feature_type='cli',
        injector_feature_type='cli_inject',
        argv=sys.argv[1:],
        seed_data={},
    ))
```

```toml
# my_app/pyproject.toml
[project.scripts]
my-app = "my_app.cli:cli_dispatch"
```

`cli_dispatch` takes no parameters: a generated console script calls its
target with no arguments, so `sys.argv[1:]` is read here, at the one place
that owns the process boundary.  Every argument the engine takes is passed
explicitly, per [[:no-default-values]].

Because the engine is a plain coroutine, dispatch is reusable wherever a loop
is already running — no second `asyncio.run()`, no `nest_asyncio`, no thread.
Call the engine itself; there is nothing else in between:

```python
# From an MCP tool handler, a Starlette route, or a test:
await cli_dispatch_engine(
    cli_feature_type='cli',
    injector_feature_type='cli_inject',
    argv=['greet', 'name=Alice'],
    seed_data={},
)
```

Seed data is where the application injects its context object; the engine
passes it straight to `di.with_seed_data(...)`:

```python
await cli_dispatch_engine(
    cli_feature_type='cli',
    injector_feature_type='cli_inject',
    argv=argv,
    seed_data={XCtx: xctx},
)
```
