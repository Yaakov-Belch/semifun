import inspect
import functools
from semifun.caching.dictdefault import dictdefault


def cached_method(fn):
    """Decorator that caches method results by hashed arguments.

    Example::

        @dataclass(frozen=True)
        class MyService:
            cache_codec: Inject[TmsgpackCodec]
            ...

            @cached_method
            def get_config(self, env: str) -> Config: ...

            @cached_method
            async def fetch_user(self, user_id: int) -> User: ...
    """
    sig = inspect.signature(fn)
    params = list(sig.parameters.keys())
    assert params and params[0] == 'self'
    cache_attr = f'_method_cache_{fn.__name__}'
    is_async = inspect.iscoroutinefunction(fn)
    dd = dictdefault.a if is_async else dictdefault

    # Build a signature without 'self' for normalization
    norm_sig = sig.replace(parameters=[sig.parameters[p] for p in params[1:]])

    def _get_cache(self):
        try:
            return getattr(self, cache_attr)
        except AttributeError:
            cache = {}
            object.__setattr__(self, cache_attr, cache)
            return cache

    def _make_key(self, args, kwargs):
        bound = norm_sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return self.cache_codec.hash_to_bytes(bound.args + tuple(bound.kwargs.items()))

    if is_async:
        @functools.wraps(fn)
        async def wrapper(self, *args, **kwargs):
            key = _make_key(self, args, kwargs)
            return await dd(_get_cache(self), key, lambda: fn(self, *args, **kwargs))
        return wrapper
    else:
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            key = _make_key(self, args, kwargs)
            return dd(_get_cache(self), key, lambda: fn(self, *args, **kwargs))
        return wrapper
