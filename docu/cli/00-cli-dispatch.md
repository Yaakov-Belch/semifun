[[cli-dispatch]]
# CLI Dispatch: declare CLI functions with `#::cli:`

* CLI dispatch connects command-line invocations to feature functions.
* sync and async functions
* `int`, `float`, `bool` arguments: automatically converted
* positional and 'key=value' keyword arguments
* dependency injection with `Inject[T]`
* unknown commands, `--help`: signatures and docstrings
* pyproject.toml CLI command configuration -- shortcut for one command per project

```python
from semifun.di.model import Inject

#::cli:overdue
def overdue(due_date:str, copies: int = 1, patron_type: str='student'):
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
$ library bogus                 # error, the same listing, exit status 1
```

```toml
# pyproject.toml
[project.scripts]
library = "semifun.cli.dispatch:semifun_cli"
```
