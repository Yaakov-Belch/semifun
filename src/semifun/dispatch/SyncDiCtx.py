"""Sync mirror of AsyncDiCtx.

KEEP IN SYNC with AsyncDiCtx.py — this is a mechanical transformation:
  - drop async/await
  - dictdefault.a -> dictdefault
  - isasyncgen / isawaitable branches -> TypeError
  - aclose -> close
When you change one, apply the same change to the other.
"""
from __future__ import annotations

from dataclasses import dataclass
from inspect import isasyncgen, isawaitable, isgenerator, signature
from typing import TYPE_CHECKING

from semifun.caching.cached_property import cached_property
from semifun.caching.dictdefault import dictdefault

from .Inject import injected_type
from .tools import factory_field

if TYPE_CHECKING:
    from .SemifunApp import SemifunApp


@dataclass(frozen=True)
class SyncDiCtx:
    app: SemifunApp
    parent_ctx: SyncDiCtx | None
    seed_data: dict
    ftype: str

    _cleanup_stack: list = factory_field(list)


    @cached_property
    def _cache(self): return {**self.seed_data, SyncDiCtx: self}

    def resolve_type(self, T):
        def compute_type():
            args, kwargs = getattr(T, 'dependency_injection_args2', ((), {}))
            return self.fname_call_inject(fname=T.__name__, args=args, kwargs=kwargs)
        return dictdefault(self._cache, T, compute_type)

    def resolve_fn_ctx(self, *, ftype_suffix, fname):
        ftype = self.ftype + ftype_suffix
        if fn := self.app.lookup_fn(ftype=ftype, fname=fname, strict=False):
            return (fn, self)
        elif self.parent_ctx:
            return self.parent_ctx.resolve_fn_ctx(ftype_suffix=ftype_suffix, fname=fname)

    def fn_call(self, *, fn, args, kwargs):
        """Call fn with passthrough args/kwargs, resolving Inject[T] params via DI."""
        inject_kwargs = {}
        for p in signature(fn).parameters.values():
            T = injected_type(p.annotation)
            if T is not None:
                inject_kwargs[p.name] = self.resolve_type(T)
        result = fn(*args, **kwargs, **inject_kwargs)
        if isgenerator(result):
            value = next(result)
            self._cleanup_stack.append(result)
            return value
        if isasyncgen(result):
            raise TypeError(f"sync DI context cannot handle async generator from {fn}")
        if isawaitable(result):
            raise TypeError(f"sync DI context cannot handle awaitable from {fn}")
        return result

    def fname_call(self, *, fname, args, kwargs):
        fn, ctx2 = self.resolve_fn_ctx(ftype_suffix='', fname=fname)
        return ctx2.fn_call(fn=fn, args=args, kwargs=kwargs)

    def fname_call_inject(self, *, fname, args, kwargs):
        fn, ctx2 = self.resolve_fn_ctx(ftype_suffix='_inject', fname=fname)
        return ctx2.fn_call(fn=fn, args=args, kwargs=kwargs)

    def close(self):
        """Drain the cleanup stack in reverse order."""
        exception = None
        for gen in reversed(self._cleanup_stack):
            try:
                next(gen)
            except StopIteration:
                pass
            except BaseException as new_exc:
                if exception is not None:
                    new_exc.__context__ = exception
                exception = new_exc
        self._cleanup_stack.clear()
        if exception is not None:
            raise exception
