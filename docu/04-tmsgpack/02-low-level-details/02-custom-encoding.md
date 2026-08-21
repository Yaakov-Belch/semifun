[[:tmsgpack-custom-encoding]]
# Custom encoding: custom serialization for non-dataclass types

* Define custom encoder/decoders with `TmsgpackCustom`.
* Dependency-injection for advanced encode/decode patterns.

```python
from tmsgpack.codec_custom import TmsgpackCustom

class Bar:
    def __init__(self, x, y):
        self.x = x
        self.y = y

obj = Bar()
print(type(obj).__name__)  # Prints "Bar".
# This is the name to be used in registration: `#::tmsgpack_codec:Bar=...`

#::tmsgpack_codec:Bar=CodecBar
# Define exactly one encode/decode pair.  Choose one of three wire formats:

# Dict mode — key-value pairs, decoded as **kwargs:
class CodecBar(TmsgpackCustom):
    def encode_dict(obj):     return {'x': obj.x, 'y': obj.y}
    def decode_dict(*, x, y): return Bar(x=x, y=y)

# List mode — ordered sequence, decoded as positional args:
class CodecBar(TmsgpackCustom):
    def encode_list(obj):     return [obj.x, obj.y]
    def decode_list(x, y):    return Bar(x, y)

# Bytes mode — raw bytes, decoded from a single bytes argument:
class CodecBar(TmsgpackCustom):
    def encode_bytes(obj):    return struct.pack('ff', obj.x, obj.y)
    def decode_bytes(data):   return Bar(*struct.unpack('ff', data))
```

Encoding looks up `type(obj).__name__` → `"Bar"` in the feature map, finds `CodecBar`, and calls encode.  Decoding reads `"Bar"` from the wire, resolves to `CodecBar`, and calls decode.  Mismatched modes (e.g. `encode_dict` with `decode_list`) raise `TypeError` at class definition time.


## Dependency injection on custom encode/decode

Common use cases:
* External storage / blob offloading: store large data externally, send short id.
* Deduplication / interning: Replace duplicates with one content-addressed id.

```python
from semifun.di.model import Inject
# Include `BlobStore` in your `seed_data` (or via an injector function).

#::tmsgpack_codec:Big=CodecBig
class CodecBig(TmsgpackCustom):
    def encode_dict(obj, store: Inject[BlobStore]):
        blob_id = store.put(obj.data)
        return {'id': blob_id, 'name': obj.name}
    def decode_dict(*, id, name, store: Inject[BlobStore]):
        data = store.get(id)
        return Big(name=name, data=data)
```
