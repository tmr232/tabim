import bisect
import functools
import operator
from operator import attrgetter
from typing import Optional, NewType, List

import attr
import guitarpro.models


@attr.frozen
class Note:
    start: int
    end: int
    string: int
    fret: int


@attr.define
class Measure:
    notes: List[Note]

    @property
    def columns(self):
        # This is terrible code, but we need to start somewhere.
        start_times = sorted({note.start for note in self.notes})

        for start in start_times:
            # Collect all the notes that start or continue at given time
            starting = [note for note in self.notes if note.start == start]
            cont = [note for note in self.notes if note.start < start < note.end]

            # Convert to display notes
            # We start with the continuation notes to handle silly mistakes
            strings = {n: DisplayNote() for n in range(1, 7)}
            for note in cont:
                strings[note.string] = DisplayNote(
                    cont_in=True,
                    cont_out=True,
                    cont=True,
                    fret=note.fret,
                )
            for note in starting:
                strings[note.string] = attr.evolve(
                    strings[note.string],
                    fret=note.fret,
                    cont=False,
                    cont_out=True,
                )

            yield [note for _, note in sorted(strings.items())]


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


Column = NewType("Column", List[DisplayNote])


@attr.define
class String:
    notes: List[Note]

    def __getitem__(self, timestamp: int) -> DisplayNote:
        starts = [note.start for note in self.notes]


def parse_measure(measure: guitarpro.models.Measure) -> Measure:
    notes = []

    for voice in measure.voices:
        for beat in voice.beats:
            for note in beat.notes:
                notes.append(
                    Note(
                        start=beat.startInMeasure,
                        end=beat.startInMeasure + beat.duration.time,
                        fret=note.value,
                        string=note.string,
                    )
                )
    return Measure(notes=sorted(notes, key=attrgetter("start")))


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


def render_measure(measure: Measure, column_width: int) -> str:
    return functools.reduce(
        concat_columns,
        map(lambda col: render_column(col, column_width), measure.columns),
        "\n".join("|" * 6),
    )
