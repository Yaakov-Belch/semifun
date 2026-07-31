[[di-injector-with-resource-cleanup]]
# Injector cleanup: the `yield` pattern releases resources at the end of the call

* Register resource cleanup with a context manager or with the yield pattern.
* Code after `yield` runs when the top-level DI call finishes.


Injectors that acquire resources (connections, file handles) use the `yield`
pattern.

```python
from typing import Iterator

#::z_injector:DbConnection=open_connection
def open_connection(*, zctx: Inject[ZCtx]) -> Iterator[DbConnection]:
    conn = connect(zctx.db_url)
    try:
        yield conn
    finally:
        conn.close()
```
