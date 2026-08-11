[[tmsgpack:custom-encoding]]
# Custom encoding: custom serialization for non-dataclass types

* How to define custom encode/decode logic for types that are not dataclasses.
* Subclass `TmsgpackCustom` and define one encode/decode pair: dict, list, or bytes mode.
* `Inject[T]` works on both encode and decode signatures.


## Basics

Register a `TmsgpackCustom` subclass with the `#::` comment.  The key
before `=` is the type name used on the wire and for lookup; the class
below the comment is the codec handler, not the type itself:

```python
from tmsgpack.codec_custom import TmsgpackCustom

class Bar:
    def __init__(self, x, y):
        self.x = x
        self.y = y

#::tmsgpack_codec:Bar=CodecBar
class CodecBar(TmsgpackCustom):
    def encode_dict(obj):
        return {'x': obj.x, 'y': obj.y}
    def decode_dict(*, x, y):
        return Bar(x=x, y=y)
```

Encoding a `Bar` instance looks up `type(obj).__name__` → `"Bar"` in the
feature map, finds `CodecBar`, and calls `encode_dict`.  Decoding reads
`"Bar"` from the wire, resolves to `CodecBar`, and calls `decode_dict`.


## Wire modes

Define exactly one encode/decode pair.  The mode determines the wire
format and which `EncodeCtx`/`DecodeCtx` methods are used:

**Dict mode** — key-value pairs, decoded as `**kwargs`:

```python
class CodecBar(TmsgpackCustom):
    def encode_dict(obj):
        return {'x': obj.x, 'y': obj.y}
    def decode_dict(*, x, y):
        return Bar(x=x, y=y)
```

**List mode** — ordered sequence, decoded as positional args:

```python
class CodecBar(TmsgpackCustom):
    def encode_list(obj):
        return [obj.x, obj.y]
    def decode_list(x, y):
        return Bar(x, y)
```

**Bytes mode** — raw bytes, decoded from a single bytes argument:

```python
import struct

class CodecPoint(TmsgpackCustom):
    def encode_bytes(obj):
        return struct.pack('ff', obj.x, obj.y)
    def decode_bytes(data):
        x, y = struct.unpack('ff', data)
        return Point(x, y)
```

Mismatched modes (e.g. `encode_dict` with `decode_list`) raise `TypeError`
at class definition time.


## Dependency injection

`Inject[T]` parameters on encode or decode are filled by the codec's
dependency injector, the same way dataclass `Inject[T]` fields work on
decode ([[tmsgpack:di-on-decode]]).

```python
from semifun_dependency_injection.model import Inject

#::tmsgpack_codec:Big=CodecBig
class CodecBig(TmsgpackCustom):
    def encode_dict(obj, store: Inject[BlobStore]):
        blob_id = store.put(obj.data)
        return {'id': blob_id, 'name': obj.name}
    def decode_dict(*, id, name, store: Inject[BlobStore]):
        data = store.get(id)
        return Big(name=name, data=data)
```

DI detection happens once when the codec handler is created (first
encode or decode of that type).  Subsequent calls go through the cached
handler with no signature inspection overhead.


### Use cases for DI on encode

**External storage / blob offloading.**  Large or shared data is stored
in an external service during encode; only a short identifier goes on the
wire.  Decode retrieves the data by identifier.  The service handle
(`BlobStore`, S3 client, database connection) is injected.

**Deduplication / interning.**  When many objects carry identical copies
of the same data, encode stores the data once and replaces duplicates with
a reference.  This is the same external-storage pattern with a
content-addressed store: encode hashes the data, stores it if new, and
writes the hash to the wire.  Decode resolves the hash back to the shared
data.

Both patterns require a service handle that the object itself should not
know about — exactly what `Inject[T]` provides.


## Validation

`TmsgpackCustom.__init_subclass__` validates at class definition time:

* Exactly one of `encode_dict`, `encode_list`, `encode_bytes` must be defined.
* Exactly one of `decode_dict`, `decode_list`, `decode_bytes` must be defined.
* The encode and decode modes must match.

The `isinstance(..., TmsgpackCustom)` check in `codec_spec_to_codec_handler`
runs **before** `is_dataclass`, so a `@dataclass` decorator on a
`TmsgpackCustom` subclass is harmless — the custom path takes priority.
