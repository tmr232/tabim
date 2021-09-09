import io

import typer
from pathlib import Path
from typing import Optional
import guitarpro

from tabim.measure import build_measure, parse_notes
from tabim.render import render_columns


def main(gp_path: Path, out_path: Optional[Path] = None):
    with gp_path.open("rb") as stream:
        tab = guitarpro.parse(stream)

    track = tab.tracks[0]

    output = io.StringIO()

    for bar, gp_measure in enumerate(track.measures, start=1):

        measure = build_measure(gp_measure)
        print(bar, file=output)
        print(render_columns(measure.columns, 8), file=output)

    if out_path:
        with out_path.open("w") as f:
            f.write(output.getvalue())
    else:
        print(output.getvalue())


if __name__ == "__main__":
    typer.run(main)
