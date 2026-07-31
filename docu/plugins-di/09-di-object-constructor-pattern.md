[[di-object-constructor-pattern]]
# Stateful features: register a frozen dataclass, DI calls it as a constructor

* How to create handler objects with dependency injection.
* DI treats the class as a constructor function with the same signature as its fields.


When a feature needs to hold state across multiple method calls, register a
`@dataclass(frozen=True)` class.

```python
#::feature_handler:sql_db_connector=SqlDbConnector
@dataclass(frozen=True)
class SqlDbConnector:
    dbh: Inject[DbHandle]
    user_name: Inject[UserName]

    async def api_get_balance(self) -> float: ...
    async def api_transfer(self, recipient: str, amount: float) -> str: ...
```
