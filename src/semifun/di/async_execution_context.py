"""Per-call async execution context for dependency injection.

A new `_AsyncExecutionContext` is created for each public async DI API call.
It holds the per-call state (resolution cache, cleanup stack, cycle-detection
lock) and delegates signature lookups to the parent `DependencyInjector`.

This module is internal — the public API lives on `DependencyInjector`.

**THIS IS THE SOURCE OF TRUTH FOR THE DI EXECUTION LOGIC.** Any changes here
must be propagated to `sync_execution_context.py` following the rules in
`SYNC-CONVERSION.md`.
"""

from dataclasses import dataclass, field
from inspect import isasyncgen, isawaitable, isgenerator
from typing import Any, Callable, TYPE_CHECKING

from .model import InjectArg
from .signature_processing import cache_key_for

if TYPE_CHECKING:
    from .injector import DependencyInjector


@dataclass(frozen=True)
class _AsyncExecutionContext:
    """One async DI execution. Created fresh per public API call, disposed at end.

    Holds:
    - `cache`: Type → resolved value, seeded from seed_data
    - `cleanup_stack`: generators awaiting their final next/anext for cleanup
    - `lock`: cache keys of functions currently being invoked (cycle detection)
    - `injector`: reference to the parent DependencyInjector
    """

    injector: "DependencyInjector"
    cache: dict[type, Any] = field(init=False)
    cleanup_stack: list[Any] = field(default_factory=list, init=False)
    lock: set[Any] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        # Shallow copy of seed_data, plus auto-seed DependencyInjector for re-entrant DI access.
        object.__setattr__(self, 'cache', {**self.injector.seed_data, type(self.injector): self.injector})

    # --- Resolution of one injected argument ---

    async def _resolve_inject_arg(self, arg: InjectArg) -> Any:
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
        value = await self._invoke_call_with_args(arg.injector_fn, args=(), kwargs={})
        if not isinstance(value, arg.type):
            raise TypeError(
                f"Injector for {arg.type.__name__!r} returned a value of type "
                f"{type(value).__name__!r} which is not an instance of "
                f"{arg.type.__name__!r}."
            )
        self.cache[arg.type] = value
        return value

    # --- Invoking functions with DI ---

    async def _invoke_call_with_args(
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
                inject_kwargs[arg.name] = await self._resolve_inject_arg(arg)
            return await self._handle_result(fn(*args, **kwargs, **inject_kwargs))
        finally:
            self.lock.discard(key)

    # --- Handling fn's return value (generator / async-generator / awaitable / value) ---

    async def _handle_result(self, result: Any) -> Any:
        """Process whatever the function returned.

        - sync generator → take first yield, push to cleanup stack
        - async generator → await first yield, push to cleanup stack
        - awaitable (coroutine) → await it
        - plain value → return as-is
        """
        if isgenerator(result):
            gen = result
            value = next(gen)
            self.cleanup_stack.append(gen)
            return value
        if isasyncgen(result):
            gen = result
            value = await gen.__anext__()
            self.cleanup_stack.append(gen)
            return value
        if isawaitable(result):
            return await result
        return result

    # --- Cleanup at end of DI execution ---

    async def _cleanup(self) -> None:
        """Drain the cleanup stack in reverse order.

        Each generator gets one more next/anext; we expect StopIteration /
        StopAsyncIteration. Other exceptions are chained and re-raised after
        all cleanups have run.
        """
        exception: BaseException | None = None
        for gen in reversed(self.cleanup_stack):
            try:
                if isasyncgen(gen):
                    await gen.__anext__()
                else:
                    next(gen)
            except (StopIteration, StopAsyncIteration):
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
