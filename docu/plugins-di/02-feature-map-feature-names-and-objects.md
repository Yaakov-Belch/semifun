[[feature_map.feature_names_and_objects]]
# Feature map: iterate over everything registered in a namespace

* Iterate over all available features — for help text, discovery, and validation.


```python
feature_map = get_cached_feature_map('z_command')

feature_map.feature_names                # ('my_balance', 'transfer') — sorted tuple of names
feature_map.feature_names_and_objects    # (('my_balance', <fn>), ('transfer', <fn>)) — sorted tuple of (name, object) pairs
```
