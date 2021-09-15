from __future__ import annotations

import io
from typing import Sequence

import guitarpro
import pytest

from tabim.config import LyricsPosition, RenderConfig
from tabim.song import (
    parse_song,
    less_naive_render_beats,
    render_measures,
    render_song,
    render_measure,
)
from tabim.types import AsciiMeasure
from tabim.utils import strip_trailing_whitespace
from tests.conftest import get_sample


def naive_render_measures(measures: Sequence[AsciiMeasure]):
    output = io.StringIO()

    for i, measure in enumerate(measures, start=1):
        print(i, file=output)
        print(render_measure(measure, show_lyrics=True), file=output)

    return strip_trailing_whitespace(output.getvalue())


@pytest.mark.parametrize(
    "sample",
    [
        "BeautyAndTheBeast.gp5",
        "DifferentNotes.gp5",
        "BasicSustain.gp5",
        "TieNote.gp5",
        "CarpetOfTheSun.gp5",
        "NoteEffects.gp5",
    ],
)
def test_parse_song(verify_tab, sample):
    with get_sample(sample).open("rb") as stream:
        song = guitarpro.parse(stream)

    tab = parse_song(song, 0)
    measures = less_naive_render_beats(tab, n_strings=len(song.tracks[0].strings))
    verify_tab(naive_render_measures(measures))


@pytest.mark.parametrize("line_length", [60, 80, 90])
@pytest.mark.parametrize(
    "sample",
    [
        "BeautyAndTheBeast.gp5",
        "DifferentNotes.gp5",
        "BasicSustain.gp5",
        "TieNote.gp5",
        "CarpetOfTheSun.gp5",
        "NoteEffects.gp5",
    ],
)
def test_render_song(verify_tab, sample, line_length):
    with get_sample(sample).open("rb") as stream:
        song = guitarpro.parse(stream)

    tab = parse_song(song, 0)
    measures = less_naive_render_beats(tab, n_strings=len(song.tracks[0].strings))
    verify_tab(render_measures(measures, line_length=line_length))


@pytest.mark.parametrize("line_length", [60, 80])
@pytest.mark.parametrize(
    "sample",
    [
        "BeautyAndTheBeast.gp5",
        "CarpetOfTheSun.gp5",
    ],
)
def test_render_full(verify_tab, sample, line_length):
    with get_sample(sample).open("rb") as stream:
        song = guitarpro.parse(stream)

    config = RenderConfig()
    config.line.lyrics_position = LyricsPosition.Top
    verify_tab(render_song(song, config=config))
