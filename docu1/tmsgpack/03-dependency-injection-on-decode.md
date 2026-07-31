[[tmsgpack:di-on-decode]]
# DI on decode: `Inject[T]` fields are never stored, always injected

* How `Inject[T]` fields are hydrated during deserialization.
* Fields annotated `Inject[T]` are excluded from serialization; on decode the injector fills them in from seed data.
* Without a `DependencyInjector`, such types fail on *encode* — the field is not recognised as injected.


```python
from semifun_dependency_injection.injector import DependencyInjector
from semifun_dependency_injection.model import Inject

#::tmsgpack_codec:Bar
@dataclass(frozen=True)
class Bar:
    dbh: Inject[DbHandle]
    x: str

# Encode: only 'x' is serialized (dbh is injected, not stored)
di = DependencyInjector(injectors_map=lookup, seed_data={DbHandle: my_dbh})
codec = TmsgpackCodec(
    sort_keys=True, di=di,
    plugin_feature_type='tmsgpack_codec',
)

data = codec.encode(bar)
restored = codec.decode(data)   # restored.dbh comes from seed_data, not the bytes

# Update seed data for a different context:
codec2 = codec.with_seed_data({DbHandle: other_dbh})
restored2 = codec2.decode(data)   # restored2.dbh == other_dbh
```

Exclusion depends on the injector: `codec_spec_to_codec_handler` asks
`di.injected_type(field.type)` which fields to leave out.  The default
`NoDependencyInjector` answers `None` for everything, so an `Inject[T]` field
is treated as an ordinary one and the codec tries to *serialize the injected
value*.  That fails during **encode**, not decode:

```
ValueError: Cannot encode this type: None
```

Types without `Inject[T]` fields work either way.
