import functools
import operator
from typing import Optional, NewType, List

import attr


@attr.s(auto_attribs=True)
class DisplayNote:
    cont_in: bool = False
    cont_out: bool = False
    cont: bool = False
    fret: Optional[int] = None


@attr.define
class RenderedNote:
    prefix: str
    postfix: str
    pre_cont: str
    post_cont: str

    def __str__(self):
        return f"{self.pre_cont}_{self.prefix}.{self.postfix}_{self.post_cont}"


@attr.s(auto_attribs=True)
class Column:
    notes: List[DisplayNote]
    division: int


def render_note(note: DisplayNote) -> RenderedNote:
    if note.cont_in:
        pre_cont = "="
    else:
        pre_cont = "-"
    if note.cont_out:
        post_cont = "="
    else:
        post_cont = "-"
    prefix = ""
    if note.cont:
        postfix = "="
    elif note.fret is None:
        postfix = "-"
    else:
        postfix = str(note.fret)

    return RenderedNote(
        prefix=prefix,
        postfix=postfix,
        pre_cont=pre_cont,
        post_cont=post_cont,
    )


def concat_columns(col1: str, col2: str) -> str:
    return "\n".join(map(operator.add, col1.splitlines(), col2.splitlines()))


import rich


def render_column(column: Column, quarter_width: int) -> str:
    rendered: List[RenderedNote] = list(map(render_note, column.notes))
    max_prefix = max(len(n.prefix) for n in rendered)
    max_postfix = max(len(n.postfix) for n in rendered)

    target_width = quarter_width * 4 // column.division

    # max_prefix = max(1, max_prefix)
    max_postfix = max(target_width, max_postfix)

    return "\n".join(
        note.prefix.rjust(max_prefix, note.pre_cont)
        + note.postfix.ljust(max_postfix, note.post_cont)
        for note in rendered
    )


def render_columns(columns, quarter_width):
    return functools.reduce(
        concat_columns,
        map(lambda col: render_column(col, quarter_width), columns),
        ("|-\n" * 6),
    )
