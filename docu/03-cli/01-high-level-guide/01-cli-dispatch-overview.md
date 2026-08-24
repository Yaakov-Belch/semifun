[[cli-dispatch]]
# CLI Dispatch: declare CLI functions with `#::cli:`

* CLI dispatch connects command-line invocations to feature functions (CLI sub-commands).
* sync and async functions supported
* `int`, `float`, `bool` arguments: automatically converted
* positional and 'key=value' keyword arguments
* dependency injection with `Inject[T]` -- see [[plugins-dependency-injection]]
* unknown commands, `--help`: signatures and docstrings
* How to define and register CLI command dispatchers

```python
from semifun.di.model import Inject

#::cli:overdue
def overdue(due_date:str, copies: int, patron_type: str):
    """Calculate the overdue fine for a late return."""
    fine = OVERDUE_RATE[patron_type] * (date.today() - parse(due_date)).days * copies
    print(f'The overdue fine is: {fine:.2f}$')

#::cli:return=return_book
async def return_book(isbn, *, dbh: Inject[DbHandle]):
    """Check a book back in."""
    await dbh.checkin(isbn)
```

```
$ library overdue 2026-07-15 3 student
$ library overdue due_date=2026-07-15 copies=3 patron_type=student
$ library return 978-0-13-468599-1

$ library overdue --help        # overdue's signature and docstring
$ library --help                # every command's signature and docstring
$ library                       # the same as: library --help
$ library bogus                 # error, the same listing
```


## How to define and register CLI command dispatchers

* One ready-made function `semifun.cli.dispatch:semifun_cli`:
  * With one `pyproject.toml` config, define one CLI-dispatcher per project.
  * Sub-commands and injectors are defined with `#::cli:` and `#::cli_inject`.

```toml
[project.scripts]
my_cli_command = "semifun.cli.dispatch:semifun_cli"
```

For more CLI commands, copy the definition of `semifun_cli` and adjust the arguments:

```python
import asyncio, sys

from semifun.cli.dispatch import cli_dispatch_engine

def semifun_cli():
    asyncio.run(cli_dispatch_engine(
        feature_type='cli',
        argv=sys.argv[1:],
        extra_kwargs=None,
        seed_data={},
        help_output=print,
    ))
```

Insight: For CLI-dispatchers, `seed_data={}` is natural:  The function `semifun_cli()`
does not receive any arguments.  It has nothing that can be passed into `seed_data`.
Every context (`os.environ`, file system, network) can be accessed equally from injectors.
