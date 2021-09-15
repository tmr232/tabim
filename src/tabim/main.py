import typer
from pathlib import Path
from typing import Optional
import guitarpro

from tabim.song import render_song


def main(gp_path: Path, out_path: Optional[Path] = None):
    with gp_path.open("rb") as stream:
        song = guitarpro.parse(stream)

    rendered_song = render_song(song)

    if out_path:
        with out_path.open("w") as f:
            f.write(rendered_song)
    else:
        print(rendered_song)


if __name__ == "__main__":
    typer.run(main)
