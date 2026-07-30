"""Type-cast CLI string arguments based on function signature annotations.

Self-contained — uses only the standard library's inspect module.
Handles regular parameters, *args with element-level annotations,
and **kwargs with element-level annotations.
"""

import inspect
from typing import Any


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

    # Separate params by kind
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

    # Cast positional args
    for i, value in enumerate(args):
        if i < len(positional_params):
            annotation = positional_params[i].annotation
        elif var_positional is not None:
            annotation = var_positional.annotation
        else:
            annotation = inspect.Parameter.empty
        cast_positional.append(_cast_value(annotation, value))

    # Cast keyword args
    for key, value in kwargs.items():
        if key in keyword_params:
            annotation = keyword_params[key].annotation
        elif key in {p.name for p in positional_params}:
            # Named arg matching a positional param
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
