import guitarpro

from tabim.tabim import DisplayNote, render_column, parse_measure, render_measure
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
