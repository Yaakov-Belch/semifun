# argv parsing and type casting

A CLI argument containing `=` is a keyword argument (split at the first `=` only).
All other arguments are positional.

Python `int`, `float`, `bool` arguments are auto-converted.
`bool` understands: `0`/`1`/`true`/`false`/`yes`/`no`.

```
#::cli:show_the_args
def show_the_args(who:str, age_str, age:float, *bools:bool, *, city, query):
   print(f'The args are:\n{who=} {age_str=} {age=} {bools=} {city=} {query=}')

$ show_the_args Bob 50 50 true 0 false city=Jerusalem query=a=b=c
The args are:
who='Bob' age_str='50' age=50 bools=[True, False, False] city='Jerusalem' query='a=b=c'
```
