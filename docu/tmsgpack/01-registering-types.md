[[tmsgpack:registering-types]]
# Registering types: `#::tmsgpack_codec:TypeName` above the dataclass or enum

* How to register dataclasses and enums for automatic serialization.
* The feature type defaults to `'tmsgpack_codec'` (configurable via `plugin_feature_type` on `TmsgpackCodec`).


```python
#::tmsgpack_codec:Foo
@dataclass(frozen=True)
class Foo:
    x: str
    y: int

#::tmsgpack_codec:Priority
class Priority(enum.IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
```

Encoding serializes dataclass fields as a dict keyed by attribute name.
Decoding resolves the type name from the wire format via the plugin
feature map, then reconstructs: `constructor(**fields)`.
