from __future__ import annotations

import io
import re
from collections import deque
from itertools import groupby
from operator import attrgetter
from typing import Iterable, Any, Optional, Iterator, Sequence

import attr
import guitarpro
import pytest
import rich
from more_itertools import windowed, chunked

from tabim.note import render_note
from tests.conftest import get_sample


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


@attr.s(auto_attribs=True)
class TabNote:
    note: guitarpro.Note
    prev_note: Optional[TabNote]
    is_play: bool = False
    is_cont: bool = False
    tie_note: Optional[TabNote] = None

    @property
    def fret(self):
        cur = self
        while cur.tie_note:
            cur = cur.tie_note
        return cur.note.value

    @property
    def is_tie(self):
        return bool(self.tie_note)

    @staticmethod
    def play(
        note: guitarpro.Note, prev_note: Optional[guitarpro.Note] = None
    ) -> TabNote:
        return TabNote(
            note=note,
            is_play=True,
            prev_note=prev_note,
        )

    @staticmethod
    def cont(
        note: guitarpro.Note, prev_note: Optional[guitarpro.Note] = None
    ) -> TabNote:
        return TabNote(
            note=note,
            is_cont=True,
            prev_note=prev_note,
        )

    @staticmethod
    def tie(
        note: guitarpro.Note,
        tie_note: TabNote,
    ) -> TabNote:
        # Propagate cont
        return TabNote(
            note=note,
            tie_note=tie_note,
            is_cont=tie_note.is_cont,
            prev_note=tie_note,
        )

    def set_cont(self):
        self.is_cont = True

        # Propagate up tie-notes!
        tie_note = self.tie_note
        while tie_note:
            tie_note.is_cont = True
            tie_note = tie_note.tie_note


@attr.s(auto_attribs=True)
class TabBeat:
    start: int
    notes: list[TabNote] = attr.Factory(list)
    is_measure_break: bool = False
    is_rest: bool = False
    lyric: str = ""

    @staticmethod
    def from_notes(
        start: int, notes: list[TabNote], lyric: Optional[str] = None
    ) -> TabBeat:
        return TabBeat(notes=notes, lyric=lyric, start=start)

    @staticmethod
    def measure(start: int) -> TabBeat:
        return TabBeat(is_measure_break=True, start=start)


def get_measure_beats(measure: guitarpro.Measure) -> list[guitarpro.Beat]:
    beats = unnest(measure.voices, "beats")
    return sorted(beats, key=attrgetter("start"))


def get_grouped_beats(
    measure: guitarpro.Measure,
) -> Iterator[tuple[int, Iterator[guitarpro.Beat]]]:
    return groupby(get_measure_beats(measure), key=attrgetter("start"))  # type:ignore


def parse_lyrics(
    lyric_line: guitarpro.LyricLine, track: guitarpro.Track
) -> dict[int, str]:
    timestamps = []
    for measure in track.measures[lyric_line.startingMeasure - 1 :]:
        for beat in measure.voices[0].beats:
            if beat.status != guitarpro.BeatStatus.normal:
                continue
            timestamps.append(beat.start)

    lyric_fragments = [
        "".join(parts).strip()
        for parts in chunked(re.split("([- \n]+)", lyric_line.lyrics), 2)
    ]

    return dict(zip(timestamps, lyric_fragments))


def parse_song(song: guitarpro.Song, track_number: int = 0):
    """
    The idea is that we break the song up into yet another new kind of beat.
    This itme, the beat holds notes of the following types:

        * ``Play(note)`` - this is where the note starts
        * ``Cont(note)`` - The note is still active
        * ``Tie(note, into)`` - Ties to the previous note. Also holds the original note.

    So that later we can iterate and know what to render.
    Additionally, a beat can also have a "measure-bound" type so that
    we just know to draw it.

    The idea is that as we traverse the notes, we build the beats to
    hold all the relevant information.
    Later, when we actually draw - we traverse in pairs (or triplets?) to
    know how to apply effects and continuations.
    But the basic knowledge of whether to apply continuations is already present.

    Beats will also hold info on whether they are "Strong" beats (quarters in 4/4, for example)
    and the relevant lyric fragment.
    """
    track = song.tracks[track_number]

    lyric_timestamps = parse_lyrics(song.lyrics.lines[0], track)

    tab_beats = []
    live_notes: list[Optional[TabNote]] = [None for _ in track.strings]
    for measure in track.measures:
        for timestamp, beats in get_grouped_beats(measure):
            tie_live_notes = live_notes[:]
            # Remove all ended live-notes
            for string, note in enumerate(live_notes):
                if not note:
                    continue
                if note.note.beat.start + note.note.beat.duration.time <= timestamp:
                    live_notes[string] = None

            # Collect new notes from current beats
            notes: list[Optional[TabNote]] = [None for _ in track.strings]
            new_live_notes = live_notes[:]
            tie_notes = []
            has_play = False  # Denotes whether any play-note was present in the beat
            for beat in beats:
                for note in beat.notes:
                    if note.type == guitarpro.NoteType.tie:
                        new_note = TabNote.tie(
                            note, tie_note=tie_live_notes[note.string - 1]
                        )
                        tie_notes.append(new_note)
                    else:
                        new_note = TabNote.play(
                            note, prev_note=tie_live_notes[note.string - 1]
                        )
                        has_play = True
                    new_live_notes[note.string - 1] = new_note
                    notes[note.string - 1] = new_note
            if has_play:
                for tie_note in tie_notes:
                    tie_note.set_cont()

            # Mark continuation for live notes
            for string, (note, live_note) in enumerate(zip(notes, live_notes)):
                if note:
                    continue
                if live_note and has_play:
                    notes[string] = TabNote.cont(
                        live_note.note, tie_live_notes[live_note.note.string - 1]
                    )
                    # Propagate cont
                    live_note.set_cont()

            # Update live notes
            live_notes = new_live_notes

            tab_beats.append(
                TabBeat.from_notes(
                    notes=notes,
                    lyric=lyric_timestamps.get(timestamp, ""),
                    start=timestamp,
                )
            )

        tab_beats.append(TabBeat.measure(start=measure.end))

    return tab_beats


def try_getattr(obj: Optional[Any], attr: str) -> Any:
    attrs = str.split(attr, ".")
    for name in attrs:
        if obj is None:
            break
        obj = getattr(obj, name)
    return obj


def less_naive_render_beats(beats: Sequence[TabBeat], n_strings: int = 6) -> str:
    lyrics = []
    strings = [[] for _ in range(n_strings)]

    measures = []

    measure_break_notes = [True for _ in range(n_strings)]

    for beat in beats:
        if beat.is_measure_break:
            measures.append((lyrics, strings))
            lyrics = []
            strings = [[] for _ in range(n_strings)]
            measure_break_notes = [True for _ in range(n_strings)]
            continue

        ascii_notes = [
            render_note(
                note=try_getattr(note, "note"),
                prev=try_getattr(note, "prev_note.note"),
            )
            for note in beat.notes
        ]

        max_head = max(len(note.head) for note in ascii_notes)
        max_tail = max(
            len(beat.lyric),
            max(len(note.tail) for note in ascii_notes),
        )

        draw_width = max(3, max_head + max_tail + 1)
        draw_tail = draw_width - max_head

        lyrics.append(" " * max_head + beat.lyric.ljust(draw_tail))
        for i, (note, ascii_note) in enumerate(zip(beat.notes, ascii_notes)):
            # No note, so we just draw the empty state
            if not note:
                strings[i].append("-" * draw_width)
                continue

            # If the previous note is a cont, we need to pad with a cont
            head_pad = "-"
            if note.prev_note and note.prev_note.is_cont:
                head_pad = "="

            # If this is a cont, pad with a cont
            tail_pad = "-"
            if note.is_cont:
                tail_pad = "="

            base = ""
            head = 0
            tail = 0
            if note.is_play or (note.is_tie and measure_break_notes[i]):
                base = ascii_note.note
                head = len(ascii_note.head)
                tail = len(ascii_note.tail)

            rendered = (
                head_pad * (max_head - head) + base + tail_pad * (draw_tail - tail)
            )

            measure_break_notes[i] = False

            strings[i].append(rendered)

    output = io.StringIO()

    for i, (lyrics, strings) in enumerate(measures, start=1):
        print(i, file=output)
        print("".join(lyrics).rstrip(), file=output)
        for string in strings:
            print("".join(string).rstrip(), file=output)
        print(file=output)

    return output.getvalue()


def naive_render_beats(beats: list[TabBeat], n_strings: int = 6) -> str:
    lyrics = []
    strings = [[] for _ in range(n_strings)]

    measures = []

    measure_break_notes = [True for _ in range(n_strings)]

    for beat in beats:
        if beat.is_measure_break:
            measures.append((lyrics, strings))
            lyrics = []
            strings = [[] for _ in range(n_strings)]
            measure_break_notes = [True for _ in range(n_strings)]
            continue
        width = max(3, len(beat.lyric) + 1)
        lyrics.append(beat.lyric.ljust(width))
        for i, note in enumerate(beat.notes):
            if not note:
                strings[i].append("-" * width)
                continue
            base = ""
            pad = "-"
            if note.is_play:
                base = str(note.fret)
            if note.is_cont:
                pad = "="
            if note.is_tie and measure_break_notes[i]:
                base = f"({note.fret})"

            measure_break_notes[i] = False

            strings[i].append(base.ljust(width, pad))

    output = io.StringIO()

    for i, (lyrics, strings) in enumerate(measures, start=1):
        print(i, file=output)
        print("".join(lyrics).rstrip(), file=output)
        for string in strings:
            print("".join(string).rstrip(), file=output)
        print(file=output)

    return output.getvalue()


@pytest.mark.parametrize(
    "sample",
    [
        "BeautyAndTheBeast.gp5",
        "DifferentNotes.gp5",
        "BasicSustain.gp5",
        "TieNote.gp5",
        "CarpetOfTheSun.gp5",
    ],
)
def test_parse_song(verify_tab, sample):
    with get_sample(sample).open("rb") as stream:
        song = guitarpro.parse(stream)

    tab = parse_song(song, 0)
    verify_tab(less_naive_render_beats(tab, n_strings=len(song.tracks[0].strings)))


@pytest.mark.parametrize(
    "sample",
    [
        "BeautyAndTheBeast.gp5",
        "DifferentNotes.gp5",
        "BasicSustain.gp5",
        "TieNote.gp5",
        "CarpetOfTheSun.gp5",
    ],
)
def test_line_breaks(verify_tab, sample):
    with get_sample(sample).open("rb") as stream:
        song = guitarpro.parse(stream)

    track = song.tracks[0]
    for measure in track.measures:
        print(measure.lineBreak)
