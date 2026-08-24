import inspect
import functools
from inspect import isawaitable
from semifun.caching.dictdefault import dictdefault


def cached_function(
    fn, *, fn_cache, result_cache, cache_codec,
):
    """Replace a deterministic function by a cached version.

    fn_cache = {}
    result_cache = {}
    cache_codec = ...

    def fn(...): ... # expensive computation (both sync and async supported)
    ---
    cached_fn = cached_function(
        fn=fn, fn_cache=fn_cache, result_cache=result_cache, cache_codec=cache_codec,
    )
    ---
    result = await cached_fn(...) # Same result as `fn(...)`, computed once only.

    Two caches serve different roles:
    - fn_cache: Multiple calls to `cached_function(fn, fn_cache, ...)` produce
      the same cached result: You can now call `cached_function` repeatedly.
    - result_cache: Cache for the computation results.
    """
    sig = inspect.signature(fn)

    def _make_key(args, kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return cache_codec.hash_to_bytes(bound.args + tuple(bound.kwargs.items()))

    def wrap_fn():
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            async def _call():
                res = fn(*args, **kwargs)
                if isawaitable(res):
                    return await res
                return res

            key = _make_key(args, kwargs)
            return await dictdefault.a(result_cache, key, _call)
        return wrapper

    return dictdefault(fn_cache, fn, wrap_fn)
