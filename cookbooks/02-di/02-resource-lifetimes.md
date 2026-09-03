# Managing Resource Lifetimes: DBConnection vs. DBSession

A `DBConnection` lives as long as the server process; a `DBSession` lives only for one request.  Both must be closed when done with.  Only functions that need one receive it — there is no coupling between skill signatures that need different resources.

We need scoped lifecycle management with on-demand creation: each resource is instantiated lazily, shared within its scope, and torn down automatically when that scope closes — with nested scopes so a request scope inherits from the application scope.

We use:
* `#::` comments to register skills, injectors, and infrastructure,
* `Inject[T]` to request a resource (cached and shared within each scope),
* generator factories with `yield` to create and later release resources,
* `parent_scope` for scope inheritance — a request scope sees app-scoped resources.

```python
# ── tiny_xcontext/db.py ──────────────────────────────────────────────

from pymongo import MongoClient
from semifun.dispatch.Inject import Inject


class DBConnection: ...
class DBSession: ...
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


#::skill_inject:DBSession=get_DBSession
def get_DBSession(conn: Inject[DBConnection]):
    """Request-scoped: one session per skill call, auto-closed."""
    session = conn.start_session()
    try:
        yield session
    finally:
        session.end_session()


# ── tiny_xcontext/skills/items.py ────────────────────────────────────

from semifun.dispatch.Inject import Inject

#::skill:get_items
def get_items(collection: str, db: Inject[DBSession], reply: Inject[ReqReply]):
    items = db[collection].find()
    reply('\n'.join(str(item) for item in items))


#::skill:put_item
def put_item(collection: str, doc: dict, db: Inject[DBSession], reply: Inject[ReqReply]):
    db[collection].insert_one(doc)
    reply('Inserted.')


# ── tiny_xcontext/server.py (dispatch wiring) ───────────────────────

from semifun.dispatch.SemifunApp import SemifunApp

app = SemifunApp(entry_points_group='tiny_xcontext.app')

async def handle_skill_call(skill_name, args, kwargs):
    await app.async_dispatch(
        parent_scope=app_scope,       # long-lived, holds DBConnection
        seed_data={},
        ftype='skill',
        fname=skill_name,
        args=args,
        kwargs=kwargs,
    )


# ── tiny_xcontext/startup.py (app scope lifecycle) ──────────────────

async def run_server(config):
    async with app.open_async_scope(
        parent_scope=None,
        seed_data={ServerConfig: config},
        ftype='server',
    ) as app_scope:
        # app_scope stays open for the server's lifetime.
        # DBConnection is created on first Inject[DBConnection],
        # cached in app_scope, closed when app_scope exits.
        await serve_forever(app_scope)
```
