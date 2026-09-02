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

    def resolve_fn_ctx(self, *, ftype_suffix, fname):
        ftype = self.ftype + ftype_suffix
        if fn := self.app.lookup_fn(ftype, fname, strict=False): return (fn, self)
        elif self.parent_ctx: return self.parent_ctx.resolve_fn_ctx(ftype_suffix, fname)

    async def fn_call(self, *, fn, args, kwargs):
        DI magic: signature(fn), Inject, dependency_injection_args2, recursion

    async def fname_call(self, *, fname, args, kwargs):
        fn, ctx2 = self.resolve_fn_ctx(self, fname=fname, ftype_suffix='')
        return await ctx2.fn_call(fn=fn, args=args, kwargs=kwargs)
