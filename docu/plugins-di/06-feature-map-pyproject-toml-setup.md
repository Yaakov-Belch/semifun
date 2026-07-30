[[feature_map:pyproject.toml:setup]]
# Activating a package: one entry-point line makes its `#::` features visible

* Required one-time `pyproject.toml` setup to activate comment-scanning.
* Without it, the package's features are invisible.


```toml
[project.entry-points."feature_plugins.default"]
your_package = "your_package"
```
