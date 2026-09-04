# Managing Resource Lifetimes: DBConnection vs. ReqReply

A `DBConnection` lives as long as the server process and must be closed on shutdown.  A `ReqReply` is created fresh for each request and needs no cleanup.  Both are injected into skill functions the same way — the skill author doesn't know which has lifecycle management behind it and which doesn't.

We need scoped lifecycle management with on-demand creation: a resource is instantiated lazily on first use, shared within its scope, and torn down automatically when that scope closes.  Not every resource needs teardown — some are simply seeded into a scope as ready-to-use values.  Nested scopes let a request scope inherit long-lived resources from the application scope.

We use:
* `#::` comments to register skills and injectors,
* `Inject[T]` to request a resource (cached and shared within each scope),
* generator factories with `yield` to create resources that need cleanup,
* `seed_data` to place ready-to-use values into a scope without a factory,
* `parent_scope` for scope inheritance — a request scope sees app-scoped resources.

```python
# ── tiny_xcontext/db.py ──────────────────────────────────────────────

from pymongo import MongoClient
from semifun.dispatch.Inject import Inject


class DBConnection: ...
class ServerConfig: ...


#::server_inject:DBConnection=get_DBConnection
def get_DBConnection(config: Inject[ServerConfig]):
    """App-scoped: one connection for the lifetime of the server."""
    if config.db_type == 'polodb':
        conn = PoloDB(config.db_path)
    else:
        conn = MongoClient(config.db_url)
    try:
        yield conn
    finally:
        conn.close()


# ── tiny_xcontext/reply.py ───────────────────────────────────────────

class ReqReply:
    """Collects reply messages for one request.  No cleanup needed."""
    def __init__(self):
        self.messages = []

    def __call__(self, text, **kwargs):
        self.messages.append((text, kwargs))

    def response_str(self):
        return '\n'.join(text for text, _ in self.messages)


# ── tiny_xcontext/skills/items.py ────────────────────────────────────

from semifun.dispatch.Inject import Inject

#::skill:get_items
def get_items(collection: str, db: Inject[DBConnection], reply: Inject[ReqReply]):
    items = db[collection].find()
    reply('\n'.join(str(item) for item in items))


#::skill:put_item
def put_item(collection: str, doc: dict, db: Inject[DBConnection], reply: Inject[ReqReply]):
    db[collection].insert_one(doc)
    reply('Inserted.')


# ── tiny_xcontext/server.py ─────────────────────────────────────────

from semifun.dispatch.SemifunApp import SemifunApp

app = SemifunApp(entry_points_group='tiny_xcontext.app')


async def handle_skill_call(skill_name, kwargs, *, app_scope):
    """Dispatch one skill call inside a per-request scope."""
    reply = ReqReply()
    await app.async_dispatch(
        parent_scope=app_scope,             # inherits DBConnection
        seed_data={ReqReply: reply},         # no factory, no cleanup
        ftype='skill',
        fname=skill_name,
        args=(),
        kwargs=kwargs,
    )
    return reply.response_str()


# ── tiny_xcontext/startup.py ────────────────────────────────────────

async def run_server(config):
    async with app.open_async_scope(
        parent_scope=None,
        seed_data={ServerConfig: config},
        ftype='server',
    ) as app_scope:
        # app_scope stays open for the server's lifetime.
        # DBConnection is created on first Inject[DBConnection],
        # cached here, closed when app_scope exits.
        await serve_forever(app_scope)
```
