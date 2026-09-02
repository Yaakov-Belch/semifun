# `run_all_plugins`: call every feature in a namespace

Calls every registered feature of a given `plugin_type` with dependency injection.
Like `di_plugin_feature`, uses the baked-in convention: injectors come from `plugin_type + '_inject'`.
Used for startup hooks, middleware registration, and similar "run all" patterns.

```python
from semifun.di.run_all_plugins import run_all_plugins

# Collect results from all plugins (e.g. instruction strings):
parts = await run_all_plugins(
    plugin_type='mcp_server_instructions',
    seed_data=mcp_server_instructions_seed_data,
)
instructions = '\n\n'.join(parts)

# Run all plugins for side effects (e.g. registering routes):
await run_all_plugins(
    plugin_type='fastmcp_server_setup',
    seed_data={FastMCP: mcp_server, **fastmcp_server_setup_seed_data},
)
```
