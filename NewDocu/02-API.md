[project.entry-points."semifun.dispatch.app"]
experiments = "experiments"

SemifunApp()
    app = load_dispatch_app(entry_points_group = 'semifun.dispatch.app')
    app.async_dispatch(parent_ctx, seed_data, ftype, fname, args, kwargs)
    app.async_dispatch_all(parent_ctx, seed_data, ftype, args, kwargs)
    app.open_async_di_ctx(parent_ctx, seed_data, ftype)
    app.lookup_fn(ftype, fname, strict)
    app.fn_items(ftype)

AsyncDiCtx(app, parent_ctx, seed_data, ftype,   cache, cleanup_stack)
    di_ctx.resolve_type(T)
    di_ctx.resolve_fn_ctx(ftype_suffix, fname, strict)
    di_ctx.fn_call(fn, args, kwargs)
    di_ctx.fname_call(fname, args, kwargs)
    di_ctx.aclose()

sig = signature_without_Inject(fn) # inspect.Signature

@dataclass(frozen=True)
class SemifunApp:
    async def async_dispatch(self, parent_ctx, seed_data, ftype, fname, args, kwargs):
        async with self.open_async_di_ctx(parent_ctx, seed_data, ftype) as di_ctx:
            fn, ctx2 = di_ctx.resolve_fn(ftype_suffix='', fname, strict=True)
            return await ctx2.fn_call(fn, args, kwargs)

    async def async_dispatch_all(self, parent_ctx, seed_data, ftype, args, kwargs):
        async with self.open_async_di_ctx(parent_ctx, seed_data, ftype) as di_ctx:
            return {
                fname: di_ctx.fn_call(fn, args, kwargs)
                for fname, fn in self.fn_items(ftype)
            }

    @asynccontextmanager
    def open_async_di_ctx(self, parent_ctx, seed_data, ftype):
        di_ctx = AsyncDiCtx(app=self, parent_ctx, seed_data, ftype)
        try: yield di_ctx
        finally: await di_ctx.aclose()

    def lookup_fn(self, ftype, fname, strict):
        if res := self._lookup_tables.get(ftype, {}).get(fname, None): return res.fn
        if strict: raise KeyError(f'#::{ftype}:{fname}')
        return None

    def fn_items(self, ftype):

@dataclass(frozen=True)
class AsyncDiCtx:
    app: SemifunApp
    parent_ctx: AsyncDiCtx | None
    seed_data: dict
    ftype: str

    cache: dict = factory_field(dict)
    cleanup_stack: list = factory_field(list)

    async def resolve_type(self, T):
        async def compute_type()
            args, kwargs = getattr(T, 'dependency_injection_args2', ((), {}))
            return self.fname_call(fname=T.__name__, args=args, kwargs=kwargs)
        return await dictdefault.a(self.cache, T, compute_type)

    def resolve_fn_ctx(self, ftype_suffix, fname):
        ftype = self.ftype + ftype_suffix
        if fn := self.app.lookup_fn(ftype, fname, strict=False): return (fn, self)
        elif self.parent_ctx: return self.parent_ctx.resolve_fn_ctx(ftype_suffix, fname)

    async def fn_call(self, fn, args, kwargs):
        DI magic: signature(fn), Inject, dependency_injection_args2, recursion

    async def fname_call(self, fname, args, kwargs):
        fn, ctx2 = self.resolve_fn_ctx(self, fname=fname, ftype_suffix='')
        return await ctx2.fn_call(fn=fn, args=args, kwargs=kwargs)



def load_dispatch_app(entry_points_group):
    ...

@dataclass(frozen=True)
class ModuleLoader:
    dotted_module_name: str

    @cached_property
    def module(self): return importlib.import_module(self.dotted_module_name)

def _dotted_module_name(root_package_name: str, relative_path: str) -> str:
    """Compose the dotted module name for a file inside an installed package.

    Examples:
        ('foo', 'bar/foobar.py')   -> foo.bar.foobar
        ('foo', 'bar/__init__.py') -> foo.bar
        ('foo', '__init__.py')     -> foo
    """

    parts = list(Path(relative_path).with_suffix('').parts)
    if parts and parts[-1] == '__init__':
        parts.pop()
    return '.'.join([root_package_name, *parts])


@dataclass(frozen=True)
class FnLoader:
    module_loader: ModuleLoader
    fname: str

    @cached_property
    def fn(self): return getattr(self.module_loader.module, self.fname)



