import guitarpro
import rich
import pytest
import io
from approvaltests import verify, verify_with_namer
from approvaltests.pytest.namer import PyTestNamer
from tabim.measure import build_measure, parse_notes
from tabim.render import (
    DisplayNote,
    render_column,
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


@pytest.mark.parametrize(
    "sample",
    [
        "BeautyAndTheBeast.gp5",
        "DifferentNotes.gp5",
        "BasicSustain.gp5",
        "TieNote.gp5",
    ],
)
def test_render(request, sample):
    with open(get_sample(sample), "rb") as stream:
        tab = guitarpro.parse(stream)

    track = tab.tracks[0]

    output = io.StringIO()

    for bar, gp_measure in enumerate(track.measures, start=1):
        notes = parse_notes(gp_measure)

        measure = build_measure(notes)
        print(bar, file=output)
        print(render_columns(measure.columns, 8), file=output)

    namer = PyTestNamer(request=request)
    verify_with_namer(output.getvalue(), namer=namer)


def test_measure():
    with open(get_sample("BeautyAndTheBeast.gp5"), "rb") as stream:
        tab = guitarpro.parse(stream)

    track = tab.tracks[0]

    for bar, gp_measure in enumerate(track.measures, start=1):
        notes = parse_notes(gp_measure)

        measure = build_measure(notes)
        print()
        print(bar)
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
