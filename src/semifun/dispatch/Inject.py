from typing import get_args, get_origin

type Inject[T] = T


def injected_type(annotation) -> type | None:
    """If annotation is Inject[T], return T. Otherwise return None."""
    if get_origin(annotation) is Inject:
        args = get_args(annotation)
        if len(args) == 1:
            return args[0]
    return None
