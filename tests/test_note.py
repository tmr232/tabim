import io
from itertools import islice, chain
from operator import attrgetter
from typing import Iterator, Optional

import guitarpro
import rich
from more_itertools import take, windowed

from tests.conftest import get_sample

import attr


@attr.s(auto_attribs=True)
class AsciiNote:
    head: str
    tail: str

    def __str__(self):
        return self.head + self.tail


def render_note(
    note: guitarpro.Note,
    prev: Optional[guitarpro.Note],
) -> str:
    if note.type == guitarpro.NoteType.normal:
        if prev and prev.effect.hammer:
            if prev.value > note.value:
                return f"p{note.value}"
            else:
                return f"h{note.value}"

        if note.effect.isHarmonic:
            if isinstance(note.effect.harmonic, guitarpro.NaturalHarmonic):
                return f"<{note.value}>"

        if prev and prev.effect.slides:
            if prev.effect.slides[0] == guitarpro.SlideType.legatoSlideTo:
                if prev.value > note.value:
                    return f"\\{note.value}"
                else:
                    return f"/{note.value}"
            if prev.effect.slides[0] == guitarpro.SlideType.shiftSlideTo:
                return f"s{note.value}"

        if note.effect.isBend:
            bend = note.effect.bend
            if bend.type in (guitarpro.BendType.bend, guitarpro.BendType.bendRelease):
                parts = [f"{note.value}"]
                for frm, to in windowed(
                    chain([0], map(attrgetter("value"), bend.points)), 2
                ):
                    if frm < to:
                        parts.append(f"b{note.value + to//2}")
                    elif frm > to:
                        parts.append(f"r{note.value + to//2}")
                return "".join(parts)

        if note.effect.isTrill:
            return f"{note.value}tr{note.effect.trill.fret}"

        if note.effect.vibrato:
            return f"{note.value}~"

        if note.effect.isDefault or note.effect.hammer or note.effect.slides:
            # Hammers affect the _next_ note.
            # Same goes for slides
            return f"{note.value}"

    if note.type == guitarpro.NoteType.tie:
        if prev:
            return ""

    if note.type == guitarpro.NoteType.rest:
        return ""

    if note.type == guitarpro.NoteType.dead:
        return "x"

    raise NotImplementedError()


def _iter_notes(song: guitarpro.Song) -> Iterator[guitarpro.Note]:
    track = song.tracks[0]
    for measure in track.measures:
        voice = measure.voices[0]
        for beat in voice.beats:
            yield from beat.notes


def test_note(verify):
    with open(get_sample("NoteEffects.gp5"), "rb") as stream:
        song = guitarpro.parse(stream)

    output = io.StringIO()
    prev = None
    for note in _iter_notes(song):
        try:
            print(render_note(note, prev=prev))
        except NotImplementedError:
            rich.print(note)
        prev = note

    return
    for bar, gp_measure in enumerate(track.measures, start=1):
        measure = build_measure(gp_measure)
        print(bar, file=output)
        print(render_columns(measure.columns, 8), file=output)

    verify(output.getvalue())
