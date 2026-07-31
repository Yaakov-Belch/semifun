[[multi-namespaces-feature-reuse]]
# Sharing a feature across namespaces: repeat the registration, or register an import

* Two registrations on one function.
* Or a registration on an imported name.


When the same injector or feature is needed in multiple namespaces, you can
share it directly:

```python
# Option 1: two registrations on one function
#::z_injector:UserName=get_user_name
#::other_injector:UserName=get_user_name
def get_user_name(*, zctx: Inject[ZCtx]) -> UserName:
    return UserName(zctx.user_name)

# Option 2: register an imported function
from z_app.injectors import get_user_name
#::other_injector:UserName=get_user_name
```
