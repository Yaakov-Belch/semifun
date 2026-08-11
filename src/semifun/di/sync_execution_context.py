"""Per-call sync execution context for dependency injection.

**THIS FILE IS DERIVED FROM `async_execution_context.py`.** It is not the source
of truth. Any changes to the DI execution logic must be made in the async file
first, then propagated here following the rules in `SYNC-CONVERSION.md`.

A new `SyncExecutionContext` is created for each public sync DI API call.
It holds the per-call state (resolution cache, cleanup stack, cycle-detection
lock) and delegates signature lookups to the parent `DependencyInjector`.

This module is internal — the public API lives on `DependencyInjector`.
"""

from dataclasses import dataclass, field
from inspect import isasyncgen, isawaitable, isgenerator
from typing import Any, Callable, TYPE_CHECKING

from .model import InjectArg
from .signature_processing import cache_key_for

if TYPE_CHECKING:
    from .injector import DependencyInjector


@dataclass(frozen=True)
class SyncExecutionContext:
    """One sync DI execution. Created fresh per public API call, disposed at end.

    Holds:
    - `cache`: Type → resolved value, seeded from seed_data
    - `cleanup_stack`: generators awaiting their final next for cleanup
    - `lock`: cache keys of functions currently being invoked (cycle detection)
    - `injector`: reference to the parent DependencyInjector
    """

    injector: "DependencyInjector"
    cache: dict[type, Any] = field(init=False)
    cleanup_stack: list[Any] = field(default_factory=list, init=False)
    lock: set[Any] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        # Shallow copy of seed_data, plus auto-seed the execution context itself.
        object.__setattr__(self, 'cache', {
            **self.injector.seed_data,
            SyncExecutionContext: self,
        })

    # --- Resolution of one injected argument ---

    def _resolve_inject_arg(self, arg: InjectArg) -> Any:
        """Resolve one InjectArg to a value.

        Order:
        1. Cache hit → return cached value.
        2. No cache and no injector → raise.
        3. Otherwise call the injector recursively, isinstance-check, cache, return.
        """
        if arg.type in self.cache:
            return self.cache[arg.type]
        if arg.injector_fn is None:
            raise LookupError(
                f"Cannot resolve injection for parameter {arg.name!r}: "
                f"type {arg.type.__name__!r} is not in seed_data and no injector "
                f"is registered for that type name."
            )
        value = self.invoke_call_with_args(arg.injector_fn, args=(), kwargs={})
        if not isinstance(value, arg.type):
            raise TypeError(
                f"Injector for {arg.type.__name__!r} returned a value of type "
                f"{type(value).__name__!r} which is not an instance of "
                f"{arg.type.__name__!r}."
            )
        self.cache[arg.type] = value
        return value

    # --- Invoking functions with DI ---

    def invoke_call_with_args(
        self,
        fn: Callable[..., Any],
        args: tuple,
        kwargs: dict[str, Any],
    ) -> Any:
        """Call `fn` with passthrough args/kwargs plus resolved Inject[T] args.

        Python's call mechanism does the passthrough/keyword matching, default
        filling, and conflict detection (e.g. caller kwargs cannot collide with
        injected names — Python raises 'multiple values for keyword argument').
        """
        key = cache_key_for(fn)
        if key in self.lock:
            raise RecursionError(
                f"Circular dependency detected: {_fn_name(fn)} is already being resolved."
            )
        self.lock.add(key)
        try:
            sig = self.injector.cached_call_with_args_signature(fn)
            inject_kwargs: dict[str, Any] = {}
            for arg in sig.injected_args:
                inject_kwargs[arg.name] = self._resolve_inject_arg(arg)
            return self._handle_result(fn(*args, **kwargs, **inject_kwargs))
        finally:
            self.lock.discard(key)

    # --- Handling fn's return value (generator / value) ---

    def _handle_result(self, result: Any) -> Any:
        """Process whatever the function returned.

        - sync generator → take first yield, push to cleanup stack
        - async generator → ERROR (sync DI cannot drive async injectors)
        - awaitable (coroutine) → ERROR (sync DI cannot await)
        - plain value → return as-is
        """
        if isgenerator(result):
            gen = result
            value = next(gen)
            self.cleanup_stack.append(gen)
            return value
        if isasyncgen(result):
            # Cannot close an async generator from sync code; let GC handle it.
            raise TypeError(
                "Sync DI cannot use async-generator injectors. "
                "Use the async DI API or rewrite the injector as a sync generator."
            )
        if isawaitable(result):
            # Close the coroutine so Python does not warn about an unawaited one.
            close = getattr(result, "close", None)
            if close is not None:
                close()
            raise TypeError(
                "Sync DI cannot use async (coroutine) injectors. "
                "Use the async DI API or rewrite the injector as a sync function."
            )
        return result

    # --- Cleanup at end of DI execution ---

    def _cleanup(self) -> None:
        """Drain the cleanup stack in reverse order.

        Each generator gets one more next; we expect StopIteration. Other
        exceptions are chained and re-raised after all cleanups have run.
        """
        exception: BaseException | None = None
        for gen in reversed(self.cleanup_stack):
            try:
                next(gen)
            except StopIteration:
                pass
            except BaseException as new_exc:
                if exception is not None:
                    new_exc.__context__ = exception
                exception = new_exc
        self.cleanup_stack.clear()
        if exception is not None:
            raise exception


def _fn_name(fn: Callable[..., Any]) -> str:
    return getattr(fn, "__name__", repr(fn))
