[[tmsgpack]]
# Typed MessagePack: dataclasses and enums round-trip, values hash to stable keys

* `tmsgpack` serializes Python values to compact binary (MessagePack) with type awareness — dataclasses and enums round-trip automatically when registered via `#::` comments.
* Content hashing produces stable, url-safe keys for content-addressable storage.
* Two codec tiers: `BasicCodec` for plain values, `TmsgpackCodec` for the full type system with plugin discovery and optional dependency injection.


```python
from tmsgpack.api import basic_codec
from tmsgpack.codec import NoDependencyInjector, TmsgpackCodec

# --- BasicCodec: plain values only ---

data = basic_codec.encode({'key': [1, 2, 3]})
value = basic_codec.decode(data)                # {'key': [1, 2, 3]}

# --- TmsgpackCodec: dataclasses and enums ---

#::tmsgpack_codec:Item
@dataclass(frozen=True)
class Item:
    name: str
    quantity: int

codec = TmsgpackCodec(
    sort_keys=True,
    di=NoDependencyInjector(),
    plugin_feature_type='tmsgpack_codec',
)
item = Item(name='widget', quantity=5)

data = codec.encode(item)       # → bytes
restored = codec.decode(data)   # → Item(name='widget', quantity=5)

# --- Content hashing ---

codec.hash_to_bytes(item)       # → 16 bytes (xxh3_128)
codec.hash_to_str(item)         # → 22-char url-safe base64 string
```
