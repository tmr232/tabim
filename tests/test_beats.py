from __future__ import annotations

import io
import re
from collections import deque
from itertools import groupby
from operator import attrgetter
from typing import Iterable, Any, Optional, Iterator

import attr
import guitarpro
import pytest
import rich
from more_itertools import windowed, chunked

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
    def play(note: guitarpro.Note) -> TabNote:
        return TabNote(note=note, is_play=True)

    @staticmethod
    def cont(note: guitarpro.Note) -> TabNote:
        return TabNote(note=note, is_cont=True)

    @staticmethod
    def tie(note: guitarpro.Note, tie_note: TabNote) -> TabNote:
        # Propagate cont
        return TabNote(note=note, tie_note=tie_note, is_cont=tie_note.is_cont)

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
            for beat in beats:
                for note in beat.notes:
                    if note.type == guitarpro.NoteType.tie:
                        play = TabNote.tie(note, tie_live_notes[note.string - 1])
                    else:
                        play = TabNote.play(note)
                    new_live_notes[note.string - 1] = play
                    notes[note.string - 1] = play

            # Mark continuation for live notes
            for string, (note, live_note) in enumerate(zip(notes, live_notes)):
                if note:
                    continue
                if live_note:
                    notes[string] = TabNote.cont(live_note.note)
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


def naive_render_beats(beats: list[TabBeat], n_strings: int = 6) -> str:
    lyrics = []
    strings = [[] for _ in range(n_strings)]

    measures = []

    for beat in beats:
        if beat.is_measure_break:
            measures.append((lyrics, strings))
            lyrics = []
            strings = [[] for _ in range(n_strings)]
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
            if note.is_tie:
                base = f"({note.fret})"

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
    verify_tab(naive_render_beats(tab))
