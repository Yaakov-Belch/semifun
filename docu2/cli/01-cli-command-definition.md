# How to define and register CLI command dispatchers

* The ready-made function `semifun.cli.dispatch:semifun_cli`:
  * With one `pyproject.toml` config, define one CLI command per project.
  * Sub-commands and injectors are defined with `#::cli:` and `#::cli_inject`.
* For more CLI commands, copy the definition of `semifun_cli` and adjust the arguments.

```toml
[project.scripts]
my_cli_command = "semifun.cli.dispatch:semifun_cli"
```

```python
import asyncio, sys

from semifun.cli.dispatch import cli_dispatch_engine

def semifun_cli():
    asyncio.run(cli_dispatch_engine(
        cli_feature_type='cli',
        injector_feature_type='cli_inject',
        argv=sys.argv[1:],
        seed_data={},
    ))
```
