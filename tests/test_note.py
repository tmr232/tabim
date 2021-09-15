from __future__ import annotations
import io
from itertools import chain
from typing import Iterator, Sequence

import guitarpro
import rich
from more_itertools import windowed

from tabim.note import render_note
from tests.conftest import get_sample


def _iter_notes(song: guitarpro.Song) -> Iterator[guitarpro.Note]:
    track = song.tracks[0]
    for measure in track.measures:
        voice = measure.voices[0]
        for beat in voice.beats:
            rich.print(beat)
            yield from beat.notes


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
