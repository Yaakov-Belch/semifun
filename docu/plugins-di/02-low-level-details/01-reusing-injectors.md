[[:reuse-injectors]]
# Reuse injectors

Put multiple `#::` comments on one function, or register an import.

```python
#::z_command_inject:UserName=get_user_name
#::other_inject:UserName=get_user_name
def get_user_name(*, zctx: Inject[ZCtx]) -> UserName:
    return UserName(zctx.user_name)
```

```python
from z_app.injectors import get_user_name
#::other_inject:UserName=get_user_name
```
