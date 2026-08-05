"""Frozen data model for the dependency injection library.

All structured data the library uses is represented as frozen dataclasses.
"""

import inspect
from dataclasses import dataclass
from typing import Any, Callable, get_args, get_origin

# `Inject[T]` is a transparent type alias: at the type-checker level it equals `T`,
# at the source level it is detectable in annotations as a parameterized alias.
# The DI library inspects raw annotations to distinguish `Inject[T]` from bare `T`.
type Inject[T] = T


def injected_type(annotation: Any) -> type | None:
    """If `annotation` is `Inject[T]`, return `T`. Otherwise return None."""
    if get_origin(annotation) is Inject:
        args = get_args(annotation)
        if len(args) == 1:
            return args[0]
    return None


def signature_without_Inject(fn: Callable[..., Any]) -> inspect.Signature:
    """Return ``fn``'s signature with ``Inject[…]`` parameters removed.

    The returned signature contains only the parameters that a caller
    supplies directly — the ones the DI framework fills in are dropped.
    """
    sig = inspect.signature(fn)
    return sig.replace(parameters=[
        p for p in sig.parameters.values()
        if injected_type(p.annotation) is None
    ])


# Sentinel for "no default value" on PassThroughArg.
class _Missing:
    def __repr__(self) -> str:
        return "MISSING"


MISSING = _Missing()


@dataclass(frozen=True)
class InjectArg:
    """One injected argument: the parameter name, the requested type, and the
    injector function (or None if no injector is registered for this type)."""
    name: str
    type: type
    injector_fn: Callable[..., Any] | None


@dataclass(frozen=True)
class PassThroughArg:
    """One pass-through argument: the parameter name, the annotated type
    (bare, not `Inject[T]`), and the default value (or `MISSING`)."""
    name: str
    type: type | None
    default_value: Any


@dataclass(frozen=True)
class CallWithArgsSignature:
    """Processed signature for a function used with `call_with_args`.
    Some parameters are pass-through (with optional defaults), some are injected
    (annotated with `Inject[T]`)."""
    injected_args: tuple[InjectArg, ...]
    passthrough_args: tuple[PassThroughArg, ...]
