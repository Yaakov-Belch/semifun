[[cli-dispatch:type-casting]]
# Type casting: annotations drive it, and only `int`/`float`/`bool` are cast

* Arguments are cast based on the target function's type annotations.
* All other annotations pass the string through unchanged.
* `*args: int` and `**kwargs: bool` cast element-wise; unannotated ones pass strings through.


```python
#::cli:variadic
async def variadic(*numbers: int):
    """Sum variadic positional args, each cast to int."""
    return sum(numbers)

# argv: ['variadic', '1', '2', '3']  →  variadic(1, 2, 3)  →  6
```

Bool accepts `0`, `1`, `true`, `false`, `True`, `False`, `yes`, `no`.
