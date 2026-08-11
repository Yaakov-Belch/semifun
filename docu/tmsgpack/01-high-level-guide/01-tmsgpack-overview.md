[[tmsgpack]]
# tmsgpack: Simple codec with dataclass support (and more)

* Just tag dataclasses (and Enums) with a `#::tmsgpack_codec:` comment.
* Bonus features: `BasicCodec` for JSON-encodable data; content hashing.
* Requires `pyproject.toml` registration.


```python
from tmsgpack.api import basic_codec
from tmsgpack.codec import NoDependencyInjector, TmsgpackCodec

# --- BasicCodec: JSON-encodable (plus `bytes`) values only ---

data = basic_codec.encode({'key': [1, 2, 3]})
value = basic_codec.decode(data)  # {'key': [1, 2, 3]}

# --- TmsgpackCodec: dataclasses and enums ---

#::tmsgpack_codec:Priority
class Priority(enum.IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2

#::tmsgpack_codec:Item
@dataclass(frozen=True)
class Item:
    name: str
    quantity: int
    priority: Priority

codec = TmsgpackCodec(
    sort_keys=True,             # Required for stable content hashing!
    di=NoDependencyInjector(),
    plugin_feature_type='tmsgpack_codec',
)
item = Item(name='widget', quantity=5, priority=Priority.HIGH)

data = codec.encode(item)       # → bytes
restored = codec.decode(data)   # → Item(name='widget', quantity=5, priority=Priority.HIGH)

# --- Content hashing ---

codec.hash_to_bytes(item)       # → 16 bytes (xxh3_128)
codec.hash_to_str(item)         # → 22-char url-safe base64 string
```

## pyproject.toml registration/activation

Add these two lines to `pyproject.toml`.  Without them, the `#::` comments are invisible.
See [[plugins-dependency-injection]].

```toml
[project.entry-points."feature_plugins.default"]
your_package = "your_package"
```
