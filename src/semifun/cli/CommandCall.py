"""CommandCall: Parse CLI-style argv into a typed, callable form.

Handles the full pipeline:
    CommandCall.from_argv(argv)     — first token → cmd, '=' tokens → kwargs
        .split_kv_args()            — separate key=value tokens into kwargs
        .with_fn(fn)                — attach function for signature-based casting
        .add_kwargs(extra)          — merge additional kwargs
        .cast_basic_types()         — cast strings to int/float/bool per fn's signature
        .help_shown(app, ftype, reply) — show help and return True if applicable
"""

import inspect
import textwrap
from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class CommandCall:
    """A command invocation being progressively resolved.

    All fields are required. Use .from_argv() for the common case.
    """
    cmd: str | None
    fn: callable | None
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    @classmethod
    def from_argv(cls, argv: list[str]) -> 'CommandCall':
        """Parse argv into cmd + positional args.

        First token becomes cmd, remaining tokens become args.
        No '=' splitting — call .split_kv_args() for that.
        """
        if not argv:
            return cls(cmd=None, fn=None, args=(), kwargs={})
        return cls(cmd=argv[0], fn=None, args=tuple(argv[1:]), kwargs={})

    def split_kv_args(self) -> 'CommandCall':
        """Separate key=value tokens from positional args into kwargs.

        Tokens containing '=' (split at the first '=') move to kwargs.
        All other tokens remain as positional args.
        """
        positional: list[Any] = []
        kv: dict[str, Any] = dict(self.kwargs)
        for token in self.args:
            if isinstance(token, str) and '=' in token:
                key, value = token.split('=', 1)
                kv[key] = value
            else:
                positional.append(token)
        return replace(self, args=tuple(positional), kwargs=kv)

    def with_fn(self, fn: Any) -> 'CommandCall':
        """Attach the target function (used by .cast_basic_types())."""
        return replace(self, fn=fn)

    def add_kwargs(self, extra: dict[str, Any]) -> 'CommandCall':
        """Merge additional kwargs (does not replace existing ones from args)."""
        if not extra:
            return self
        return replace(self, kwargs={**self.kwargs, **extra})

    def help_shown(self, *, app, ftype, reply) -> bool:
        """Show help text and return True if this is a help request.

        Help is shown when fn is not callable, or when cmd or args[0]
        is '--help'.  When fn is callable, shows help for that one
        function.  Otherwise lists all functions in the (app, ftype) scope,
        prepending 'Unknown command: {cmd}' when cmd is truthy and not
        '--help' itself.

        Collects one string and calls reply exactly once.
        """
        if (callable(self.fn)
                and self.cmd != '--help'
                and not (self.args and self.args[0] == '--help')):
            return False

        if callable(self.fn):
            text = _format_command_help(name=self.cmd, fn=self.fn)
        else:
            parts: list[str] = []
            if self.cmd and self.cmd != '--help':
                parts.append(f'Unknown command: {self.cmd}\n')
            fn_items = app.fn_items(ftype=ftype)
            if not fn_items:
                parts.append('No commands available.')
            else:
                parts.append('Available commands:\n')
                for name, fn in fn_items:
                    parts.append(_format_command_help(name=name, fn=fn))
            text = '\n'.join(parts)

        reply(text)
        return True

    def cast_basic_types(self) -> 'CommandCall':
        """Cast string args/kwargs to int/float/bool per fn's signature.

        Requires .fn to be set. Only int, float, and bool annotations
        are cast. All other types (or missing annotations) pass through.
        """
        if self.fn is None:
            raise ValueError("Cannot cast_basic_types without a function — call .with_fn(fn) first")

        sig = inspect.signature(self.fn)
        params = list(sig.parameters.values())

        positional_params: list[inspect.Parameter] = []
        var_positional: inspect.Parameter | None = None
        keyword_params: dict[str, inspect.Parameter] = {}
        var_keyword: inspect.Parameter | None = None

        for p in params:
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD):
                positional_params.append(p)
            elif p.kind == p.VAR_POSITIONAL:
                var_positional = p
            elif p.kind == p.KEYWORD_ONLY:
                keyword_params[p.name] = p
            elif p.kind == p.VAR_KEYWORD:
                var_keyword = p

        cast_positional: list[Any] = []
        for i, value in enumerate(self.args):
            if i < len(positional_params):
                annotation = positional_params[i].annotation
            elif var_positional is not None:
                annotation = var_positional.annotation
            else:
                annotation = inspect.Parameter.empty
            cast_positional.append(_cast_value(annotation, value))

        cast_kw: dict[str, Any] = {}
        for key, value in self.kwargs.items():
            if key in keyword_params:
                annotation = keyword_params[key].annotation
            elif key in {p.name for p in positional_params}:
                param = next(p for p in positional_params if p.name == key)
                annotation = param.annotation
            elif var_keyword is not None:
                annotation = var_keyword.annotation
            else:
                annotation = inspect.Parameter.empty
            cast_kw[key] = _cast_value(annotation, value)

        return replace(self, args=tuple(cast_positional), kwargs=cast_kw)


def _format_command_help(*, name: str, fn) -> str:
    """Format help text for a single command."""
    from semifun.dispatch.Inject import signature_without_Inject
    sig = signature_without_Inject(fn)
    doc = inspect.cleandoc(fn.__doc__ or '(no description)')
    indented = textwrap.indent(doc, '    ')
    return f'{name}{sig}\n{indented}\n'


def _cast_value(annotation: Any, value: str) -> Any:
    """Cast a single string value to the annotated type.

    Only int, float, and bool are cast. Everything else passes through.
    """
    if annotation is inspect.Parameter.empty:
        return value
    if annotation is int:
        return int(value)
    if annotation is float:
        return float(value)
    if annotation is bool:
        if value in ('0', 'false', 'False', 'no'):
            return False
        if value in ('1', 'true', 'True', 'yes'):
            return True
        raise ValueError(f"Cannot cast {value!r} to bool. Use 0/1/true/false/yes/no.")
    return value
