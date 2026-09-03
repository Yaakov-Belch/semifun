# === Callers ===

# --- semifun/cli/dispatch.py ---

async def cli_dispatch_engine(
    *,
    app: SemifunApp,
    ftype: str,
    argv: list[str],
    extra_kwargs: dict | None,
    seed_data: dict,
    parent_scope,
    help_output: callable,
):
    """Discover and run a CLI command with DI and type-cast arguments."""

    if not argv or argv[0] == '--help':
        _print_help(app=app, ftype=ftype, help_output=help_output)
        return

    command_name = argv[0]
    command_argv = argv[1:]

    fn = app.lookup_fn(ftype=ftype, fname=command_name, strict=False)

    if fn is None:
        help_output(f"Unknown command: {command_name}\n")
        _print_help(app=app, ftype=ftype, help_output=help_output)
        return

    if command_argv == ['--help']:
        _print_command_help(name=command_name, fn=fn, help_output=help_output)
        return

    str_args, str_kwargs = split_argv(command_argv)
    if extra_kwargs:
        str_kwargs.update(extra_kwargs)
    cast_positional, cast_kwargs = cast_args(fn, str_args, str_kwargs)

    async with app.open_async_scope(parent_scope=parent_scope, seed_data=seed_data, ftype=ftype) as scope:
        await scope.fn_call(fn=fn, args=cast_positional, kwargs=cast_kwargs)

#------------------------------

# --- xctx-server/skills/resolve_wiki_link.py ---

async def workspace_resolve_wiki_link(workspace, link: str) -> NoteSequence:
    """Resolve a [[wiki-link]] in the context of a WorkSpace."""
    from xctx_server.data.WorkSpace import WorkSpace
    reply = workspace.reply

    cmd, argv, kwargs = parse_wiki_link(link, reply)

    fn = app.lookup_fn(ftype='wiki_link_cmd', fname=cmd, strict=True)

    cached_fn = cached_function(
        fn=fn,
        fn_cache=_fn_cache,
        result_cache=_result_cache,
        cache_codec=tmsgpack_codec,
    )

    str_args, str_kwargs = split_argv(argv)
    py_args, py_kwargs = cast_args(fn, str_args, {**str_kwargs, **kwargs})

    seed_data = {
        WorkSpace: workspace,
        UserData: workspace.user_data, RequestConfig: workspace.config, ReqReply: reply,
    }
    async with app.open_async_scope(parent_scope=workspace.cli_scope, seed_data=seed_data, ftype='wiki_link_cmd') as scope:
        result = await scope.fn_call(fn=cached_fn, args=py_args, kwargs=py_kwargs)

    return _to_note_sequence(result, reply)


def parse_wiki_link(link: str, reply: ReqReply) -> tuple[str, list[str], dict[str, str]]:
    """Parse a [[wiki-link]] into (cmd, argv, kwargs).

    ""                           => ("__empty_query", [], {})
    [[foo:x:z:a=hello:b=world]]  => ("foo", ["x","z"], {"a":"hello", "b":"world"})
    [[:foo]]                     => ("__wiki_link_definition", ["foo"], {})
    [[foo]]                      => ("__plain_wiki_link", ["foo"], {})

    A leading '!' is stripped: "Insert link" feature.
    Bare text without [[ ]] brackets is an error.
    """
    if not link:
        return ('__empty_query', [], {})

    m = _BRACKET_RE.match(link)
    if not m:
        reply.raise_exception('Not a wiki link', link=link)

    inner = m.group(1)

    if inner.startswith('!'):
        inner = inner[1:]

    if ':' not in inner:
        return ('__plain_wiki_link', [inner], {})

    parts = inner.split(':')
    cmd = parts[0]

    if cmd == '':
        cmd = '__wiki_link_definition'

    argv, kwargs = split_argv(parts[1:])
    return (cmd, argv, kwargs)

#------------------------------

# === Definitions ===

# --- semifun/cli/argv.py ---

def split_argv(argv: list[str]) -> tuple[list[str], dict[str, str]]:
    """Split argv tokens into positional args and keyword args.

    Tokens containing '=' (split at the first '=') become keyword args.
    All other tokens are positional args, in their original order.

    Example:
        split_argv(['hello', 'time=now', 'world', 'age=10'])
        → (['hello', 'world'], {'time': 'now', 'age': '10'})

    Returns:
        (args, kwargs) — both contain raw strings, no type casting.
    """
    args: list[str] = []
    kwargs: dict[str, str] = {}
    for token in argv:
        if '=' in token:
            key, value = token.split('=', 1)
            kwargs[key] = value
        else:
            args.append(token)
    return args, kwargs

#------------------------------

# --- semifun/cli/cast.py ---

def cast_args(
    fn: Any,
    args: list[str],
    kwargs: dict[str, str],
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """Cast string args and kwargs to the types declared in fn's signature.

    Inspects fn's signature and casts each value:
    - Regular positional/keyword params: cast by their annotation
    - *args (VAR_POSITIONAL): cast each element by the *args annotation
    - **kwargs (VAR_KEYWORD): cast each element by the **kwargs annotation

    Only int, float, and bool are cast. All other types (or missing
    annotations) pass the string through unchanged.

    Args:
        fn: The target function whose signature provides type information.
        args: Positional arguments as strings.
        kwargs: Keyword arguments as strings.

    Returns:
        (cast_args_tuple, cast_kwargs_dict) ready for fn(*args, **kwargs).
    """
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())

    cast_positional: list[Any] = []
    cast_kwargs: dict[str, Any] = {}

    positional_params: list[inspect.Parameter] = []
    var_positional: inspect.Parameter | None = None
    keyword_params: dict[str, inspect.Parameter] = {}
    var_keyword: inspect.Parameter | None = None

    for p in params:
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD):
            positional_params.append(p)
        elif p.kind == p.VAR_POSITIONAL:
            var_positional = p
        elif p.kind == p.KEYWORD_ONLY:
            keyword_params[p.name] = p
        elif p.kind == p.VAR_KEYWORD:
            var_keyword = p

    for i, value in enumerate(args):
        if i < len(positional_params):
            annotation = positional_params[i].annotation
        elif var_positional is not None:
            annotation = var_positional.annotation
        else:
            annotation = inspect.Parameter.empty
        cast_positional.append(_cast_value(annotation, value))

    for key, value in kwargs.items():
        if key in keyword_params:
            annotation = keyword_params[key].annotation
        elif key in {p.name for p in positional_params}:
            param = next(p for p in positional_params if p.name == key)
            annotation = param.annotation
        elif var_keyword is not None:
            annotation = var_keyword.annotation
        else:
            annotation = inspect.Parameter.empty
        cast_kwargs[key] = _cast_value(annotation, value)

    return tuple(cast_positional), cast_kwargs


def _cast_value(annotation: Any, value: str) -> Any:
    """Cast a single string value to the annotated type.

    Only int, float, and bool are cast. Everything else passes through.
    """
    if annotation is inspect.Parameter.empty:
        return value
    if annotation is int:
        return int(value)
    if annotation is float:
        return float(value)
    if annotation is bool:
        if value in ('0', 'false', 'False', 'no'):
            return False
        if value in ('1', 'true', 'True', 'yes'):
            return True
        raise ValueError(f"Cannot cast {value!r} to bool. Use 0/1/true/false/yes/no.")
    return value

#------------------------------

# --- semifun/caching/cached_function.py ---

def cached_function(
    fn, *, fn_cache, result_cache, cache_codec,
):
    """Replace a deterministic function by a cached version.

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

#------------------------------

# --- semifun/caching/cached_method.py ---

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
