from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from inspect import signature

from semifun.caching.cached_property import cached_property
from semifun.caching.dictdefault import dictdefault

from .AsyncDiCtx import AsyncDiCtx
from .Inject import injected_type
from .SyncDiCtx import SyncDiCtx
from .load_lookup_tables import load_lookup_tables
from .tools import factory_field


@dataclass(frozen=True)
class SemifunApp:
    # Testing only: provide _lookup_tables directly as a dict to entry_points_group.
    entry_points_group: str | dict
    _inject_params_cache: dict = factory_field(dict)

    def inject_params(self, fn):
        """Return [(param_name, T), ...] for Inject[T] params in fn's signature. Cached."""
        return dictdefault(self._inject_params_cache, fn, lambda: [
            (p.name, T) for p in signature(fn).parameters.values()
            if (T := injected_type(p.annotation)) is not None
        ])

    @cached_property
    def _lookup_tables(self) -> dict[str, dict[str, FnLoader]]: # [ftype][fname]
        if isinstance(self.entry_points_group, dict): return self.entry_points_group
        return load_lookup_tables(entry_points_group=self.entry_points_group)

    def lookup_fn(self, *, ftype, fname, strict):
        if res := self._lookup_tables.get(ftype, {}).get(fname, None): return res.fn
        if strict: raise KeyError(f'#::{ftype}:{fname}')
        return None

    def fn_items(self, *, ftype):
        return [
            (fname, fn_loader.fn)
            for fname, fn_loader in self._lookup_tables.get(ftype, {}).items()
        ]

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

    # --- sync mirrors of async_dispatch / async_dispatch_all / open_async_di_ctx ---
    # KEEP IN SYNC: drop async/await, AsyncDiCtx -> SyncDiCtx, aclose -> close.

    def sync_dispatch(self, *, parent_ctx, seed_data, ftype, fname, args, kwargs):
        with self.open_sync_di_ctx(parent_ctx=parent_ctx, seed_data=seed_data, ftype=ftype) as di_ctx:
            fn, ctx2 = di_ctx.resolve_fn_ctx(ftype_suffix='', fname=fname)
            return ctx2.fn_call(fn=fn, args=args, kwargs=kwargs)

    def sync_dispatch_all(self, *, parent_ctx, seed_data, ftype, args, kwargs):
        with self.open_sync_di_ctx(parent_ctx=parent_ctx, seed_data=seed_data, ftype=ftype) as di_ctx:
            return {
                fname: di_ctx.fn_call(fn=fn, args=args, kwargs=kwargs)
                for fname, fn in self.fn_items(ftype=ftype)
            }

    @contextmanager
    def open_sync_di_ctx(self, *, parent_ctx, seed_data, ftype):
        di_ctx = SyncDiCtx(app=self, parent_ctx=parent_ctx, seed_data=seed_data, ftype=ftype)
        try: yield di_ctx
        finally: di_ctx.close()

    @cached_property
    def tmsgpack_codec_no_seed_data(self):
        return self.tmsgpack_codec(seed_data={})

    def tmsgpack_codec(self, *, seed_data):
        from tmsgpack.codec import TmsgpackCodec
        return TmsgpackCodec(
            sort_keys=True,
            di=_TmsgpackDiAdapter(app=self, seed_data=seed_data),
            plugin_feature_type='tmsgpack_codec',
        )


@dataclass(frozen=True)
class _TmsgpackDiAdapter:
    """Adapts SemifunApp to the DependencyInjectorProtocol expected by TmsgpackCodec."""
    app: SemifunApp
    seed_data: dict

    @staticmethod
    def injected_type(annotation):
        return injected_type(annotation)

    def with_seed_data(self, seed_data):
        return _TmsgpackDiAdapter(app=self.app, seed_data={**self.seed_data, **seed_data})

    def sync_call_with_args(self, *, fn, args, kwargs):
        with self.app.open_sync_di_ctx(parent_ctx=None, seed_data=self.seed_data, ftype='tmsgpack_codec') as ctx:
            return ctx.fn_call(fn=fn, args=args, kwargs=kwargs)


app = SemifunApp(entry_points_group='semifun.dispatch.app')

