from typing import Optional, NewType, List

import attr


@attr.define
class Note:
    cont_in: bool
    cont_out: bool
    cont: bool
    fret: Optional[int]


@attr.define
class RenderedNote:
    prefix: str
    postfix: str
    pre_cont: str
    post_cont: str

    def __str__(self):
        return f"{self.pre_cont}_{self.prefix}.{self.postfix}_{self.post_cont}"


Column = NewType("Column", List[Note])


def render_note(note: Note) -> RenderedNote:
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


def render_column(column: Column, min_width: int) -> str:
    rendered: List[RenderedNote] = list(map(render_note, column))
    max_prefix = max(len(n.prefix) for n in rendered)
    max_postfix = max(len(n.postfix) for n in rendered)

    max_prefix = max(min_width // 2, max_prefix)
    max_postfix = max(min_width // 2 + min_width % 2, max_postfix)

    return "\n".join(
        note.prefix.rjust(max_prefix, note.pre_cont)
        + note.postfix.ljust(max_postfix, note.post_cont)
        for note in rendered
    )


def test_render_column():
    column = [
        Note(
            cont_in=False,
            cont_out=False,
            cont=False,
            fret=None,
        ),
        Note(
            cont_in=False,
            cont_out=False,
            cont=False,
            fret=6,
        ),
        Note(
            cont_in=False,
            cont_out=True,
            cont=False,
            fret=6,
        ),
        Note(
            cont_in=True,
            cont_out=False,
            cont=False,
            fret=6,
        ),
        Note(
            cont_in=True,
            cont_out=True,
            cont=False,
            fret=6,
        ),
        Note(
            cont_in=True,
            cont_out=True,
            cont=True,
            fret=None,
        ),
        Note(
            cont_in=True,
            cont_out=False,
            cont=True,
            fret=6,
        ),
    ]
    print()
    print(render_column(column, 3))
