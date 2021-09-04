import guitarpro
import rich

from tabim.measure import build_measure
from tabim.tabim import (
    DisplayNote,
    render_column,
    parse_measure,
    render_measure,
    render_columns,
)
from tests.conftest import get_sample


def test_render_column():
    column = [
        DisplayNote(
            cont_in=False,
            cont_out=False,
            cont=False,
            fret=None,
        ),
        DisplayNote(
            cont_in=False,
            cont_out=False,
            cont=False,
            fret=6,
        ),
        DisplayNote(
            cont_in=False,
            cont_out=True,
            cont=False,
            fret=6,
        ),
        DisplayNote(
            cont_in=True,
            cont_out=False,
            cont=False,
            fret=6,
        ),
        DisplayNote(
            cont_in=True,
            cont_out=True,
            cont=False,
            fret=6,
        ),
        DisplayNote(
            cont_in=True,
            cont_out=True,
            cont=True,
            fret=None,
        ),
        DisplayNote(
            cont_in=True,
            cont_out=False,
            cont=True,
            fret=6,
        ),
    ]
    print()
    print(render_column(column, 8))


def test_from_gp():
    with open(get_sample("BasicSustain.gp5"), "rb") as stream:
        tab = guitarpro.parse(stream)

    track = tab.tracks[0]

    for gp_measure in track.measures:
        measure = parse_measure(gp_measure)
        print()
        print(render_measure(measure, 8))


def test_from_gp2():
    with open(get_sample("BeautyAndTheBeast.gp5"), "rb") as stream:
        tab = guitarpro.parse(stream)

    track = tab.tracks[0]

    for gp_measure in track.measures:
        measure = parse_measure(gp_measure)
        print()
        print(render_measure(measure, 8))


def test_measure():
    with open(get_sample("BeautyAndTheBeast.gp5"), "rb") as stream:
        tab = guitarpro.parse(stream)

    track = tab.tracks[0]

    for gp_measure in track.measures:
        notes = parse_measure(gp_measure).notes

        measure = build_measure(notes)
        print()
        print(render_columns(measure.columns, 8))


def test_tie_notes():
    with open(get_sample("TieNote.gp5"), "rb") as stream:
        tab = guitarpro.parse(stream)

    track = tab.tracks[0]
    measure = track.measures[0]
    voice = measure.voices[0]
    for beat in voice.beats:
        for note in beat.notes:
            rich.print(note)
