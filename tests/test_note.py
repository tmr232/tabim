from __future__ import annotations
import io
from functools import reduce
from itertools import islice, chain, repeat, groupby
from operator import attrgetter, add
from typing import Iterator, Optional, Sequence, List

import guitarpro
import rich
from more_itertools import take, windowed, interleave

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

    def render(self, width: int, prev_beat: Optional[TabBeat]) -> Sequence[str]:
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
                "-" * (max_head - len(note.head) + 1)
                + note.note
                + "-" * (draw_tail - len(note.tail))
            )

        return drawn_notes


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
                        parts.append(f"b{note.value + to // 2}")
                    elif frm > to:
                        parts.append(f"r{note.value + to // 2}")
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
            return AsciiNote(f"({prev.value})", 1)

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


def draw_beats(beats: Sequence[TabBeat], width: int = 8) -> str:
    rendered_beats = [
        beat.render(width=width, prev_beat=beat)
        for prev, beat in windowed(chain([None], beats), 2)
    ]
    output = io.StringIO()
    for line in zip(*rendered_beats):
        print("".join(line), file=output)

    return output.getvalue()


@attr.s(auto_attribs=True)
class TabMeasure:
    beats: Sequence[TabBeat]
    divisions: Sequence[int]
    strings: int


def get_end_beat(tab_measure: TabMeasure) -> TabBeat:
    notes = [None for _ in range(tab_measure.strings)]
    for beat in tab_measure.beats:
        for i, note in enumerate(beat.notes):
            if note:
                notes[i] = note

    return TabBeat(notes=notes)


def parse_measure(measure: guitarpro.Measure, strings: int = 6):
    notes = []
    timestamps = set()
    for voice in measure.voices:
        for beat in voice.beats:
            timestamps.add(beat.startInMeasure)
            for note in beat.notes:
                notes.append(note)

    beats = []
    for _, grouped_notes in groupby(
        sorted(notes, key=attrgetter("beat.startInMeasure")),
        key=attrgetter("beat.startInMeasure"),
    ):
        beat_notes: List[Optional[guitarpro.Note]] = [None for _ in range(strings)]
        for note in grouped_notes:
            beat_notes[note.string - 1] = note
        beats.append(TabBeat(notes=beat_notes))

    divisions = [
        measure.length // (end - start)
        for start, end in windowed(chain(sorted(timestamps), [measure.length]), 2)
    ]

    return TabMeasure(beats=beats, divisions=divisions, strings=strings)


def draw_measure(
    tab_measure: TabMeasure,
    quarter_width: int = 8,
    prev_beat: Optional[TabBeat] = None,
) -> str:
    rendered_beats = []
    for (prev, beat), division in zip(
        windowed(chain([prev_beat], tab_measure.beats), 2), tab_measure.divisions
    ):
        width = min(quarter_width, quarter_width * 4 // division)
        rendered_beats.append(beat.render(width=width, prev_beat=prev))

    output = io.StringIO()
    for line in zip(*rendered_beats):
        print("".join(line), file=output)

    return output.getvalue()


def _merge(column_a: str, column_b: str) -> str:
    return "\n".join(map(add, column_a.splitlines(), column_b.splitlines()))


def render_line(line_measures: Sequence[str]) -> str:
    tuning = "\n".join(reversed("EADGBe"))
    border = "\n".join(("|" * 6))
    parts = chain([tuning, border], interleave(line_measures, repeat(border)))
    return reduce(_merge, parts)


def render_track(
    track: guitarpro.Track,
    strings: int = 6,
    quarter_width: int = 8,
    line_length: int = 79,
) -> str:
    rendered_measures = []
    prev_beat = None
    for measure in track.measures:
        tab_measure = parse_measure(measure, strings=strings)
        rendered_measures.append(
            draw_measure(tab_measure, quarter_width=quarter_width, prev_beat=prev_beat)
        )
        prev_beat = get_end_beat(tab_measure)

    cur_length = 0
    lines = [[]]
    for rendered_measure in rendered_measures:
        measure_length = len(rendered_measure.splitlines()[0])
        if cur_length + measure_length < line_length:
            lines[-1].append(rendered_measure)
            cur_length += measure_length
        else:
            lines.append([rendered_measure])
            cur_length = measure_length

    rendered_lines = []
    bar_number = 1
    for line in lines:
        rendered_lines.append((bar_number, render_line(line)))
        bar_number += len(line)

    output = io.StringIO()

    for bar_number, line in rendered_lines:
        print(bar_number, file=output)
        print(line, file=output)
        print(file=output)

    return output.getvalue()


def test_note(verify):
    with open(get_sample("CarpetOfTheSun.gp5"), "rb") as stream:
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

    prev_beat = None
    for measure in song.tracks[0].measures:
        tab_measure = parse_measure(measure, strings=6)
        print(draw_measure(tab_measure, quarter_width=8, prev_beat=prev_beat))
        print()
        prev_beat = get_end_beat(tab_measure)

    rendered_track = render_track(song.tracks[0], line_length=90)
    print(rendered_track)
    verify(rendered_track)
