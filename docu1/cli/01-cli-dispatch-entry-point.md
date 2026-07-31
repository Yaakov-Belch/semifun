```toml
[project.scripts]
my-app = "semifun.cli.dispatch:semifun_cli"
```

#::cli_inject:ReqReply
@dataclass
class ReqReply:
    ...

#::cli:foo
def foo(..., *, reply: Inject[ReqReply]):
    ...
    reply.error(...)
    ...

#::cli_inject:post_cli_hook
def post_cli_hook(reply: Inject[ReqReply]):
    print(reply.as_string())

[[cli-dispatch:entry-point]]
# Using the engine as your CLI dispatcher: `asyncio.run()` at the entry point only

* The application owns the event loop; the engine only runs inside it.
* A `cli_dispatch` console script that is one direct `asyncio.run()`, wired via `[project.scripts]`.
* Everywhere else, await the engine directly — there is no wrapper to reuse.


`cli_dispatch_engine` is `async` on purpose — see
[[:cli-dispatch-engine-does-not-own-the-loop]].  The loop is started once, at
the process boundary, by the application.

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
