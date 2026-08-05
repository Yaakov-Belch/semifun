[[signature_without_Inject]]
# `signature_without_Inject`: the caller-facing signature

* Returns a function's `inspect.Signature` with `Inject[…]` parameters removed.
* Use when presenting a function's interface to callers who do not supply injected arguments.


```python
from semifun.di.model import Inject, signature_without_Inject

async def echo(*, message: str, reply: Inject[ReqReply], user_data: Inject[UserData]):
    ...

sig = signature_without_Inject(echo)
# sig = (*, message: str)
```

A function using dependency injection has two kinds of parameters: those the
caller supplies and those the DI framework fills in.  When the function's
signature is shown to a caller — CLI help text, MCP tool schema generation,
API documentation — the injected parameters are noise.

`signature_without_Inject` returns a standard `inspect.Signature` with only
the caller-supplied parameters, preserving their types, defaults, and ordering.
