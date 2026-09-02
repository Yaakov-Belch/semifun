[project.entry-points."semifun.dispatch.app"]
experiments = "experiments"

from semifun.dispatch.defaults import app
    app = load_dispatch_app(entry_points_group = 'semifun.dispatch.app')

result  = await app.async_dispatch(parent_ctx, seed_data, ftype, fname, args, kwargs)
results = await app.async_dispatch_all(parent_ctx, seed_data, ftype, args, kwargs)

for fname, fn in app.fn_items(ftype): ...
    sig = signature_without_Inject(fn) # inspect.Signature

di_ctx: Inject[AsyncDiCtx]
with app.open_async_di_ctx(seed_data, ftype) as di_ctx: ...
    fn = di_ctx.resolve_fn(fname, ftype_suffix=''/'_inject', strict)
          = app.lookup_fn(ftype, fname, strict)
    result = await di_ctx.fn_call(fn, args, kwargs)
    result = await di_ctx.fname_call(fname, *args, **kwargs)


AsyncDiCtx:
    app
    parent_ctx
    seed_data
    ftype
    cache, cleanup_stack

    await di_ctx.resolve_type(T)


