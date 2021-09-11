from __future__ import annotations
import io
from itertools import chain
from typing import Iterator, Sequence

import guitarpro
import rich
from more_itertools import windowed

from tabim.note import TabBeat, render_note, render_track
from tests.conftest import get_sample


def _iter_notes(song: guitarpro.Song) -> Iterator[guitarpro.Note]:
    track = song.tracks[0]
    for measure in track.measures:
        voice = measure.voices[0]
        for beat in voice.beats:
            rich.print(beat)
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


def test_rests():
    with open(get_sample("Rests.gp5"), "rb") as stream:
        song = guitarpro.parse(stream)

    prev = None
    for note in _iter_notes(song):
        try:
            print(render_note(note, prev=prev))
        except NotImplementedError:
            rich.print(note)
        prev = note


def test_note(verify):
    with open(get_sample("CarpetOfTheSun.gp5"), "rb") as stream:
        song = guitarpro.parse(stream)

    rendered_track = render_track(song.tracks[0], line_length=90)
    print(rendered_track)
    verify(rendered_track)


# TODO: Handle rests. When a GP beat has a rest, it won't have notes.
