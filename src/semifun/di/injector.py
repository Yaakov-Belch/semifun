"""The DependencyInjector — public API of the library.

Holds:
- `injectors_map`: a callable returning the injector for a type name
- `seed_data`: type → value mapping seeded into the resolution cache
- Cached processed signatures
- The two DI API methods:
  - async_call_with_args / sync_call_with_args
- `with_seed_data`: return a copy with merged seed_data (shares sig caches)
- `injected_type`: static inspection helper
- Public inspection methods (cached) for tmsgpack and similar use cases.
"""

from dataclasses import dataclass, field
from typing import Any, Callable

from .async_execution_context import AsyncExecutionContext
from .sync_execution_context import SyncExecutionContext
from .model import (
    CallWithArgsSignature,
    injected_type,
)
from .signature_processing import (
    cache_key_for,
    process_call_with_args_signature,
)


@dataclass(frozen=True)
class DependencyInjector:
    """Bind a callable `injectors_map` and provide DI invocation methods.

    `injectors_map(name, default=...)` is the lookup function returned by the
    feature plugins registry's `get_cached_feature_map`. The DI library does
    not depend on the registry directly — any callable with that signature works.
    If `injectors_map.feature_type` exists, it is used in error messages.

    `seed_data` maps types to pre-resolved values. Use `with_seed_data` to
    create a copy with additional or overridden seed values; signature caches
    are shared with the original.
    """

    injectors_map: Callable[..., Any]
    seed_data: dict[type, Any]
    _call_with_args_sig_cache: dict[Any, CallWithArgsSignature] = field(
        default_factory=dict, init=False, repr=False
    )

    def with_seed_data(self, seed_data: dict[type, Any]) -> "DependencyInjector":
        """Return a copy with `seed_data` merged on top of the original."""
        new = DependencyInjector(
            injectors_map=self.injectors_map,
            seed_data={**self.seed_data, **seed_data},
        )
        object.__setattr__(new, '_call_with_args_sig_cache', self._call_with_args_sig_cache)
        return new

    @staticmethod
    def injected_type(annotation: Any) -> type | None:
        """If `annotation` is `Inject[T]`, return `T`. Otherwise return None."""
        return injected_type(annotation)

    # --- Public inspection methods (cached) ---

    def cached_call_with_args_signature(self, fn: Callable[..., Any]) -> CallWithArgsSignature:
        """Return the processed signature of `fn` for call_with_args. Cached."""
        key = cache_key_for(fn)
        cached = self._call_with_args_sig_cache.get(key)
        if cached is None:
            cached = process_call_with_args_signature(fn, self.injectors_map)
            self._call_with_args_sig_cache[key] = cached
        return cached

    # --- Async DI API ---

    async def async_call_with_args(
        self,
        *,
        fn: Callable[..., Any],
        args: tuple,
        kwargs: dict[str, Any],
    ) -> Any:
        """Invoke `fn` with passthrough args/kwargs and Inject[T] resolution."""
        ctx = AsyncExecutionContext(injector=self)
        try:
            return await ctx.invoke_call_with_args(fn, args, kwargs)
        finally:
            await ctx._cleanup()

    # --- Sync DI API ---

    def sync_call_with_args(
        self,
        *,
        fn: Callable[..., Any],
        args: tuple,
        kwargs: dict[str, Any],
    ) -> Any:
        """Invoke `fn` with passthrough args/kwargs and Inject[T] resolution."""
        ctx = SyncExecutionContext(injector=self)
        try:
            return ctx.invoke_call_with_args(fn, args, kwargs)
        finally:
            ctx._cleanup()
