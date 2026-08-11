[[:post-cli-hook]]
# post_cli_hook -- custom error and message reports

* When defined, `post_cli_hook` runs after every CLI command invocation.
* Case study: Domain specific output:
  * Our MCP framework responds to the caller with `respond(...)`, not with `print`.
  * Our CLI scripts want to use shared functions -- we need to support `respond`.
  * Refer to [[plugins-dependency-injection]] for details about dependency injection.

```python
from dataclasses import dataclass, field
from semifun.di.model import Inject

#::cli_inject:ReqReply

@dataclass
class ReqReply:
    responses: list[str] = field(default_factory=list)

    def respond(self, *args):
        self.responses.append(' '.join(str(a) for a in args))

    def as_string(self):
        return '\n'.join(self.responses)


#::cli_inject:post_cli_hook
def post_cli_hook(reply: Inject[ReqReply]):
    if output := reply.as_string():
        print(output)


#::cli:return=return_book
async def return_book(isbn, *, dbh: Inject[DbHandle], reply: Inject[ReqReply]):
    """Check a book back in."""
    await dbh.checkin(isbn)
    reply.respond(f'{isbn}: checked in')
```
