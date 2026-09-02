[[plugins-dependency-injection]]
# Feature plugins and dependency injection: register by comment, receive by annotation

* Feature Plugins connect feature implementations with applications — without modifying application code.
* Dependency injection decouples what the application provides (seed data) from what features request (`Inject[Type]`). Injectors recursively transform seed data into the types that features need.
* Baked-in convention: `#::{plugin_type}:` uses `#::{plugin_type}_inject:`.
* Python provides important usage patterns out-of-the-box.
* `pyproject.toml` registration/activation once per project


## Powerful patterns with standard Python features

The plugin and dependency injection libraries just match Python types to Python functions
and return Python values.  Standard Python features compose with functions and produce
powerful use patterns out-of-the-box:
* Separate positional arguments from keyword-only arguments in `def` with `*`.
* When a plugin or an injector just creates a dataclass instance, consider registering the
  dataclass itself -- the constructor is a function.  Attributes are constructor arguments
  that can be provided by `args`, `kwargs` or injected -- see `DbHandle` below.
* When you want to inject basic python values (`str`, `dict`, `list`), define a
  `type` alias as a named lookup key (see `UserId` and `MyPosts` below).

```python
# #::{namespace}:{feature_name} registers the python function/object of the same name
# in this file. Use ={alias} when names differ.

from semifun.di.model import Inject
from semifun.di.di_plugin_feature import di_plugin_feature

# --- Type aliases as named DI keys ---

type UserId = str | None

# --- Application: dispatch a command with dependency injection ---

async def dispatch_command(db_client: MongoClient, user_id: str,
                           command: str, *args, **kwargs) -> Any:
    # `seed_data`: type -> instance dict
    # `args` and `kwargs` are passed as non-Inject[T] arguments to the plugin.
    # `di_plugin_feature` raises an exception when the plugin or requested injectors
    # cannot be found.
    return await di_plugin_feature(
        plugin_type='z_command', feature=command, args=args, kwargs=kwargs,
        seed_data={MongoClient: db_client, UserId: user_id},
    )

# --- Injectors: transform seed data into what features need (recursive, cached) ---

#::z_command_inject:DbHandle
@dataclass(frozen=True)
class DbHandle:
    """Database access scoped by user authorization."""
    db_client: Inject[MongoClient]
    user_id: Inject[UserId]

    async def find(self, query: dict) -> list:
        return await self.db_client.find({**query, 'user_id': self.user_id}).to_list()

    async def insert(self, doc: dict) -> None:
        await self.db_client.insert_one({**doc, 'user_id': self.user_id})


#::z_command_inject:MyPosts=get_MyPosts
type MyPosts = list[dict]
async def get_MyPosts(*, dbh: Inject[DbHandle]) -> list[dict]:
    return await dbh.find({'document_type': 'blog_post'})


# --- Features: business logic with injected dependencies ---

#::z_command:show_my_posts
async def show_my_posts(start, count, *, my_posts: Inject[MyPosts]) -> list:
    return my_posts[start:start+count]

#::z_command:save_new_post
async def save_new_post(title: str, content: str, *, dbh: Inject[DbHandle]) -> None:
    await dbh.insert({'document_type': 'blog_post', 'title': title, 'content': content})
```


## pyproject.toml registration/activation

Add these two lines to `pyproject.toml`.  Without them, the `#::` comments are invisible.

```toml
[project.entry-points."feature_plugins.default"]
your_package = "your_package"
```
