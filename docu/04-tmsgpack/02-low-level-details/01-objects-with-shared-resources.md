[[:tmsgpack-objects-with-shared-resources]]
# Serializing business logic objects with shared resources

Business logic objects often hold references to shared resources: database handles,
caches, service clients, etc.

* Encoding removes the shared resources.
* Decoding restores them with resources from the **receiver** side.
* Mark them with `Inject[T]` — see [[plugins-dependency-injection]].

```python
from semifun.di.injector import DependencyInjector

#::tmsgpack_codec:UserProfile
@dataclass(frozen=True)
class UserProfile:
    dbh: Inject[DbHandle]      # injected — not serialized
    name: str                  # stored
    email: str                 # stored

sender_di = DependencyInjector(injectors_map=None, seed_data={DbHandle: sender_dbh})
sender_codec = TmsgpackCodec(
    sort_keys=True, di=sender_di, plugin_feature_type='tmsgpack_codec',
)
wire_data = sender_codec.encode(profile)      # Only `name` and `email` go on the wire.

receiver_di = DependencyInjector(injectors_map=None, seed_data={DbHandle: receiver_dbh})
receiver_codec = TmsgpackCodec(
    sort_keys=True, di=receiver_di, plugin_feature_type='tmsgpack_codec',
)
restored = receiver_codec.decode(wire_data)   # restored.dbh is receiver_dbh
```
Notes:
* With `di=DependencyInjector(...)`:
  - All `Inject[T]` fields will be removed on encoding and injected on decoding.
  - The senders `seed_data` is not consulted for encoding (but the same codec may decode).
  - Injectors can compute injected values from `seed_data`. See [[plugins-dependency-injection]].
* With `di=NoDependencyInjector`, `Inject[T]` attributes are not removed nor injected.
