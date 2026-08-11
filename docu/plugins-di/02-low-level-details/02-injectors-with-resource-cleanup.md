# Injector with resource cleanup

Injectors that acquire resources use `yield`. Code after `yield` runs when the top-level DI call finishes.

```python
#::z_command_inject:DbConnection=open_connection
def open_connection(*, zctx: Inject[ZCtx]) -> Iterator[DbConnection]:
    conn = connect(zctx.db_url)
    try:
        yield conn
    finally:
        conn.close()
```
