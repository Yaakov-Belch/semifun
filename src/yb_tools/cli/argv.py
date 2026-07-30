"""Parse CLI argv into positional args and keyword args.

Pure string processing — no knowledge of the target function.
"""


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
