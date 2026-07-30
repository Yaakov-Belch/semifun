[[cli-dispatch:argv-parsing]]
# argv parsing: a token is a keyword argument iff it contains `=`

* How positional and keyword arguments are parsed from argv.
* Split at the first `=` only; positional and keyword tokens can be interleaved.


```python
# argv: ['Alice', 'times=3']  →  args=('Alice',), kwargs={'times': '3'}
# argv: ['query=a=b=c']       →  kwargs={'query': 'a=b=c'}  (only first = splits)
```
