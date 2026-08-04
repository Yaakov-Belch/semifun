[[injector-naming-convention]]
# Injector naming: always `plugin_type + '_inject'`

* Every plugin namespace has exactly one injector namespace: `plugin_type + '_inject'`.
* `di_plugin_feature` and `run_all_plugins` compute it; callers do not pass it.


The injector namespace for a plugin type is always `plugin_type + '_inject'`.
`run_all_plugins` and `di_plugin_feature` compute it internally from
`plugin_type`; callers pass only `plugin_type`.

```
plugin_type          injector namespace
-----------          ------------------
cli                  cli_inject
spa_build            spa_build_inject
mcp_tool             mcp_tool_inject
z_command            z_command_inject
```

This convention means different plugin namespaces never share an injector
namespace.  Each plugin namespace may have injectors that are specific to
its context, and the naming makes the relationship explicit.
