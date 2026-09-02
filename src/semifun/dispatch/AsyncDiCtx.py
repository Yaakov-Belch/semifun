"""Async DI context.

KEEP IN SYNC with SyncDiCtx.py — that file is a mechanical transformation:
  - drop async/await
  - dictdefault.a -> dictdefault
  - isasyncgen / isawaitable branches -> TypeError
  - aclose -> close
When you change one, apply the same change to the other.
"""
from __future__ import annotations

from dataclasses import dataclass
from inspect import isasyncgen, isawaitable, isgenerator
from typing import TYPE_CHECKING

from semifun.caching.cached_property import cached_property
from semifun.caching.dictdefault import dictdefault

from .tools import factory_field

if TYPE_CHECKING:
    from .SemifunApp import SemifunApp


@dataclass(frozen=True)
class AsyncDiCtx:
    app: SemifunApp
    parent_ctx: AsyncDiCtx | None
    seed_data: dict
    ftype: str

    _cleanup_stack: list = factory_field(list)
    _resolving: set = factory_field(set)  # cycle detection: types currently being resolved


    @cached_property
    def _cache(self): return {**self.seed_data, AsyncDiCtx:self}

    async def resolve_type(self, T):
        if T in self._resolving:
            raise RecursionError(f"Circular dependency: #::{self.ftype}_inject:{T.__name__} is already being resolved")
        self._resolving.add(T)
        try:
            async def compute_type():
                args, kwargs = getattr(T, 'dependency_injection_args2', ((), {}))
                return await self.fname_call_inject(fname=T.__name__, args=args, kwargs=kwargs)
            return await dictdefault.a(self._cache, T, compute_type)
        finally:
            self._resolving.discard(T)

    def resolve_fn_ctx(self, *, ftype_suffix, fname):
        ftype = self.ftype + ftype_suffix
        if fn := self.app.lookup_fn(ftype=ftype, fname=fname, strict=False):
            return (fn, self)
        elif self.parent_ctx:
            return self.parent_ctx.resolve_fn_ctx(ftype_suffix=ftype_suffix, fname=fname)
        else:
            raise KeyError(f'#::{ftype}:{fname}')

    async def fn_call(self, *, fn, args, kwargs):
        """Call fn with passthrough args/kwargs, resolving Inject[T] params via DI."""
        inject_kwargs = {}
        for name, T in self.app.inject_params(fn):
            inject_kwargs[name] = await self.resolve_type(T)
        result = fn(*args, **kwargs, **inject_kwargs)
        if isgenerator(result):
            value = next(result)
            self._cleanup_stack.append(result)
            return value
        if isasyncgen(result):
            value = await result.__anext__()
            self._cleanup_stack.append(result)
            return value
        if isawaitable(result):
            return await result
        return result

    async def fname_call(self, *, fname, args, kwargs):
        fn, ctx2 = self.resolve_fn_ctx(ftype_suffix='', fname=fname)
        return await ctx2.fn_call(fn=fn, args=args, kwargs=kwargs)

    async def fname_call_inject(self, *, fname, args, kwargs):
        fn, ctx2 = self.resolve_fn_ctx(ftype_suffix='_inject', fname=fname)
        return await ctx2.fn_call(fn=fn, args=args, kwargs=kwargs)

    async def aclose(self):
        """Drain the cleanup stack in reverse order."""
        exception = None
        for gen in reversed(self._cleanup_stack):
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
        self._cleanup_stack.clear()
        if exception is not None:
            raise exception
