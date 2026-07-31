[[plugins-dependency-injection]]
# Feature plugins and dependency injection: register by comment, receive by annotation

* Feature Plugins connect feature implementations with applications — without modifying application code.
* Dependency injection decouples what the application provides (seed data) from what features request (`Inject[Type]`). Injectors recursively transform seed data into the types that features need.
* Our standard: These are the only mechanisms used for registration and injection across this project.


```python
# #::{namespace}:{feature_name} registers the python function/object of the same name in this file. Use ={alias} when names differ.
# All #:: registrations are discovered at startup from installed packages (see [[feature_map:pyproject.toml:setup]]).

from semifun.di.model import Inject
from semifun.di.di_plugin_feature import di_plugin_feature

# --- Application: dispatch a command with dependency injection ---

async def dispatch_z_command(zctx: ZCtx, command: str, *args, **kwargs) -> Any:
    return await di_plugin_feature(
        plugin_type='z_command', feature=command, args=args, kwargs=kwargs,
        injector_type='z_injector', seed_data={ZCtx: zctx},
    )

# --- Injectors: transform seed data into what features need ---

#::z_injector:DbHandle=get_dbh
def get_dbh(*, zctx: Inject[ZCtx]) -> DbHandle:
    return zctx.dbh

# Wrap built-in types to express specific injection semantics.
class UserName(str):
    pass

#::z_injector:UserName=get_user_name
def get_user_name(*, zctx: Inject[ZCtx]) -> UserName:
    return UserName(zctx.user_name)

# --- Features: business logic with injected dependencies ---

#::z_command:my_balance
async def my_balance(*, dbh: Inject[DbHandle], user_name: Inject[UserName]) -> float:
    return await dbh.run_sql(
        'select balance from accounts where user_name = %1', user_name,
    )

#::z_command:transfer
async def transfer(recipient: str, amount: float, *,
                   memo: str = '',
                   dbh: Inject[DbHandle], user_name: Inject[UserName]) -> str:
    await dbh.run_sql(
        'insert into transfers (from_user, to_user, amount, memo) values (%1, %2, %3, %4)',
        user_name, recipient, amount, memo,
    )
    return f'Transferred {amount} to {recipient}'
```
