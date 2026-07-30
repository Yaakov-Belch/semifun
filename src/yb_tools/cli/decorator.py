"""Decorator for sync functions that own the async event loop.

Some functions (e.g., HTTP server launchers) are sync but start their own
async event loop internally. These cannot be called from within an existing
event loop — they must use the sync DI API instead of async.

This is a supported but non-standard pattern. It is an anti-pattern for
composability: such functions never compose cleanly with other async code.
"""


def sync_function_owns_async_loop(fn):
    """Mark a sync function as owning the async event loop.

    `sync_cli_dispatch_engine` detects this attribute and uses the sync DI
    API (sync_call_with_args).  `cli_dispatch_engine`, the standard engine,
    ignores it: such a command cannot be awaited, which is why it needs the
    engine that owns the loop.  See
    [[:cli-dispatch-engine-does-not-own-the-loop]].

    Usage:
        @sync_function_owns_async_loop
        def start_server(host: str = 'localhost', port: int = 8080):
            uvicorn.run(app, host=host, port=int(port))
    """
    fn.sync_function_owns_async_loop = True
    return fn
