[[feature_map:default]]
# Feature map lookup: `LookupError` by default, `default=` to opt out

* Safe lookup with `default=None` versus exceptions for missing features.


```python
feature_map = get_cached_feature_map('z_command')

fn = feature_map(feature='transfer')                 # raises LookupError if not found
fn = feature_map(feature='transfer', default=None)   # returns None if not found
```
