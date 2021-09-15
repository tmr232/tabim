import operator
from collections import deque
from operator import attrgetter
from typing import Iterable, Any, Optional


def unnest(iterable: Iterable[Any], *attrs: str, extra: Optional[str] = None):
    items = deque(iterable)

    if attrs:
        sentinel = object()
        items.append(sentinel)
        for getter in map(attrgetter, attrs):
            while items:
                item = items.popleft()
                if item is sentinel:
                    break
                items.extend(getter(item))

    if extra:
        yield from map(attrgetter(extra), items)
    else:
        yield from items


def try_getattr(obj: Optional[Any], attr: str) -> Any:
    attrs = str.split(attr, ".")
    for name in attrs:
        if obj is None:
            break
        obj = getattr(obj, name)
    return obj


def strip_trailing_whitespace(text: str):
    return "\n".join(line.rstrip() for line in text.splitlines())


def concat_columns(col1: str, col2: str) -> str:
    return "\n".join(map(operator.add, col1.splitlines(), col2.splitlines()))
