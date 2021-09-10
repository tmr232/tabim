from __future__ import annotations
import io
from itertools import islice, chain, repeat
from operator import attrgetter
from typing import Iterator, Optional, Sequence

import guitarpro
import rich
from more_itertools import take, windowed

from tests.conftest import get_sample

import attr


@attr.s(auto_attribs=True)
class AsciiNote:
    note: str = ""
    start: int = 0

    @property
    def head(self):
        return self.note[self.start :]

    @property
    def tail(self):
        return self.note[: self.start]


@attr.s(auto_attribs=True)
class TabBeat:
    notes: Sequence[Optional[guitarpro.Note]]  #: The notes in the beat

    def render(self, width: int, prev_beat: Optional[TabBeat]):
        if prev_beat:
            prev_notes = prev_beat.notes
        else:
            prev_notes = repeat(None)

        ascii_notes = [
            render_note(note, prev) for note, prev in zip(self.notes, prev_notes)
        ]

        # Get the minimal drawing width
        max_head = max(len(note.head) for note in ascii_notes)
        max_tail = max(len(note.tail) for note in ascii_notes)
        min_width = max_head + max_tail
        # Set the draw width based on minimal and desired
        draw_width = max(min_width, width)
        draw_tail = draw_width - max_head

        drawn_notes = []
        for note in ascii_notes:
            drawn_notes.append(
                "-" * (max_head - len(note.head))
                + note.note
                + "-" * (draw_tail - len(note.tail))
            )

        return drawn_notes


def draw_beats(beats: Sequence[TabBeat], width: int = 8) -> str:
    rendered_beats = [
        beat.render(width=width, prev_beat=beat)
        for prev, beat in windowed(chain([None], beats), 2)
    ]
    for line in zip(*rendered_beats):
        print("".join(line))


def render_note(
    note: Optional[guitarpro.Note],
    prev: Optional[guitarpro.Note],
) -> AsciiNote:
    if not note:
        return AsciiNote()
    if note.type == guitarpro.NoteType.normal:
        if prev and prev.effect.hammer:
            if prev.value > note.value:
                return AsciiNote(f"p{note.value}", 1)
            else:
                return AsciiNote(f"h{note.value}", 1)

        if note.effect.isHarmonic:
            if isinstance(note.effect.harmonic, guitarpro.NaturalHarmonic):
                return AsciiNote(f"<{note.value}>", 1)

        if prev and prev.effect.slides:
            if prev.effect.slides[0] == guitarpro.SlideType.legatoSlideTo:
                if prev.value > note.value:
                    return AsciiNote(f"\\{note.value}", 1)
                else:
                    return AsciiNote(f"/{note.value}", 1)
            if prev.effect.slides[0] == guitarpro.SlideType.shiftSlideTo:
                return AsciiNote(f"s{note.value}", 1)

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
                return AsciiNote("".join(parts), 0)

        if note.effect.isTrill:
            return AsciiNote(f"{note.value}tr{note.effect.trill.fret}")

        if note.effect.vibrato:
            return AsciiNote(f"{note.value}~")

        if note.effect.isDefault or note.effect.hammer or note.effect.slides:
            # Hammers affect the _next_ note.
            # Same goes for slides
            return AsciiNote(f"{note.value}")

    if note.type == guitarpro.NoteType.tie:
        if prev:
            return AsciiNote()

    if note.type == guitarpro.NoteType.rest:
        return AsciiNote()

    if note.type == guitarpro.NoteType.dead:
        return AsciiNote("x")

    raise NotImplementedError()


def _iter_notes(song: guitarpro.Song) -> Iterator[guitarpro.Note]:
    track = song.tracks[0]
    for measure in track.measures:
        voice = measure.voices[0]
        for beat in voice.beats:
            yield from beat.notes


def _iter_beats(song: guitarpro.Song) -> Iterator[TabBeat]:
    for note in _iter_notes(song):
        yield TabBeat(notes=[note, None, None, None, None, None])


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

    draw_beats(list(_iter_beats(song)))

    return
    for bar, gp_measure in enumerate(track.measures, start=1):
        measure = build_measure(gp_measure)
        print(bar, file=output)
        print(render_columns(measure.columns, 8), file=output)

    verify(output.getvalue())
