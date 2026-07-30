"""Process function signatures into CallWithArgsSignature.

These functions are pure: given a `fn` and an `injectors_map`, they return a
processed signature dataclass. They do not call the function or hold state.

The cache for processed signatures lives on the `DependencyInjector`, not here.
"""

import inspect
from typing import Any, Callable

from .model import (
    InjectArg,
    PassThroughArg,
    CallWithArgsSignature,
    MISSING,
    injected_type,
)


def cache_key_for(fn: Callable[..., Any]) -> Any:
    """The key under which `fn`'s processed signature is cached.

    For bound methods, the underlying function (`__func__`) is used so that all
    bindings of the same method share one cache entry. For plain functions, the
    function itself is the key.
    """
    return getattr(fn, "__func__", fn)


def process_call_with_args_signature(
    fn: Callable[..., Any],
    injectors_map: Callable[..., Any],
) -> CallWithArgsSignature:
    """Process a function intended for `call_with_args`.

    Each parameter is classified as:
    - injected if its annotation is `Inject[T]`
    - pass-through otherwise (bare type or no annotation)

    Pass-through parameters may have default values.
    """
    sig = inspect.signature(fn)
    injected: list[InjectArg] = []
    passthrough: list[PassThroughArg] = []
    for p in sig.parameters.values():
        inject_type = injected_type(p.annotation)
        if inject_type is not None:
            injected.append(InjectArg(
                name=p.name,
                type=inject_type,
                injector_fn=injectors_map(inject_type.__name__, default=None),
            ))
        else:
            type_obj = (
                p.annotation if p.annotation is not inspect.Parameter.empty else None
            )
            default = (
                p.default if p.default is not inspect.Parameter.empty else MISSING
            )
            passthrough.append(PassThroughArg(
                name=p.name,
                type=type_obj,
                default_value=default,
            ))
    return CallWithArgsSignature(
        injected_args=tuple(injected),
        passthrough_args=tuple(passthrough),
    )


