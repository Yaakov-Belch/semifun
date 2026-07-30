[[cli-dispatch]]
# CLI Dispatch: declare CLI functions with `#::cli:`

* CLI dispatch connects command-line invocations to feature functions.
* sync and async functions
* `int`, `float`, `bool` arguments: automatically converted
* keyword arguments: `key=value`; all others positional
* default arguments: supported
* dependency injection with `Inject[T]`
* `--help`: signatures and docstrings


```python
#::cli:greet
def greet(name='world', times: int = 1):
    """Greet someone repeatedly."""
    print('\n'.join(f'Hello, {name}!' for _ in range(times)))

#::cli:fetch
async def fetch(url, timeout: float = 5.0):
    """Fetch a URL and return its body."""
    print(await http_get(url, timeout=timeout))

#::cli:lookup
async def lookup(key, limit: int = 10, *, dbh: Inject[DbHandle]):
    """Look a key up in the database."""
    # `dbh` does not come from argv.
    # It must be provided as DI seed_data by the dispatcher or through an injector.
    print(await dbh.query(key, limit=limit))
```

```
$ my-app greet name=Alice times=3
$ my-app greet Alice 3         # the same, positionally
$ my-app fetch url=https://example.com timeout=2.5
$ my-app lookup key=acme limit=5
$ my-app fetch --help          # fetch's signature and docstring
$ my-app --help                # every command's signature and docstring
$ my-app                       # the same as: my-app --help
$ my-app bogus                 # error, the same listing, exit status 1
```
