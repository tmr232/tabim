import guitarpro
import rich
import pytest
import io
from tabim.measure import build_measure, parse_notes
from tabim.render import (
    DisplayNote,
    render_column,
    render_columns,
    Column,
)
from tests.conftest import get_sample


def test_render_column(verify):
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
    verify(render_column(Column(notes=column, division=4), 8))


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
def test_render(verify, sample):
    with open(get_sample(sample), "rb") as stream:
        tab = guitarpro.parse(stream)

    track = tab.tracks[0]

    output = io.StringIO()

    for bar, gp_measure in enumerate(track.measures, start=1):

        measure = build_measure(gp_measure)
        print(bar, file=output)
        print(render_columns(measure.columns, 8), file=output)

    verify(output.getvalue())
