from contextlib import asynccontextmanager
from dataclasses import dataclass

from semifun.caching.cached_property import cached_property

from .AsyncDiCtx import AsyncDiCtx
from .load_lookup_tables import load_lookup_tables


@dataclass(frozen=True)
class SemifunApp:
    entry_points_group: str

    @cached_property
    def _lookup_tables(self) -> dict[str, dict[str, FnLoader]]: # [ftype][fname]
        return load_lookup_tables(entry_points_group=self.entry_points_group)

    async def async_dispatch(self, *, parent_ctx, seed_data, ftype, fname, args, kwargs):
        async with self.open_async_di_ctx(parent_ctx=parent_ctx, seed_data=seed_data, ftype=ftype) as di_ctx:
            fn, ctx2 = di_ctx.resolve_fn_ctx(ftype_suffix='', fname=fname)
            return await ctx2.fn_call(fn=fn, args=args, kwargs=kwargs)

    async def async_dispatch_all(self, *, parent_ctx, seed_data, ftype, args, kwargs):
        async with self.open_async_di_ctx(parent_ctx=parent_ctx, seed_data=seed_data, ftype=ftype) as di_ctx:
            return {
                fname: await di_ctx.fn_call(fn=fn, args=args, kwargs=kwargs)
                for fname, fn in self.fn_items(ftype=ftype)
            }

    @asynccontextmanager
    async def open_async_di_ctx(self, *, parent_ctx, seed_data, ftype):
        di_ctx = AsyncDiCtx(app=self, parent_ctx=parent_ctx, seed_data=seed_data, ftype=ftype)
        try: yield di_ctx
        finally: await di_ctx.aclose()

    def lookup_fn(self, *, ftype, fname, strict):
        if res := self._lookup_tables.get(ftype, {}).get(fname, None): return res.fn
        if strict: raise KeyError(f'#::{ftype}:{fname}')
        return None

    def fn_items(self, *, ftype):
        return [
            (fname, fn_loader.fn)
            for fname, fn_loader in self._lookup_tables.get(ftype, {}).items()
        ]
