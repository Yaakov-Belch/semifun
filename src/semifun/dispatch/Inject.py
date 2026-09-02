from inspect import signature
from typing import get_args, get_origin

type Inject[T] = T


def injected_type(annotation) -> type | None:
    """If annotation is Inject[T], return T. Otherwise return None."""
    if get_origin(annotation) is Inject:
        args = get_args(annotation)
        if len(args) == 1:
            return args[0]
    return None


def signature_without_Inject(fn):
    """Return fn's signature with Inject[…] parameters removed."""
    sig = signature(fn)
    return sig.replace(parameters=[
        p for p in sig.parameters.values()
        if injected_type(p.annotation) is None
    ])
