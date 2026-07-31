[[tmsgpack:content-hashing]]
# Content hashing: encode with sorted keys, hash with xxh3_128

* Stable content-addressable hashing for any serializable value.
* Equal values always produce the same hash regardless of dict key order.


```python
codec = TmsgpackCodec(
    sort_keys=True,                       # required: False makes hashes unstable
    di=NoDependencyInjector(),
    plugin_feature_type='tmsgpack_codec',
)

codec.hash_to_bytes(value)   # → 16 bytes
codec.hash_to_str(value)     # → 22-char url-safe base64 string
```
