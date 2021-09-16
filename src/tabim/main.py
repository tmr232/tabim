from pathlib import Path
from typing import Optional

import guitarpro
import typer

from tabim.config import HeaderConfig, LineConfig, LyricsPosition, RenderConfig
from tabim.song import render_song


def main(
    gp_path: Path,
    out_path: Optional[Path] = None,
    track_number: int = 0,
    show_title: bool = True,
    center_title: bool = True,
    show_subtitle: bool = True,
    show_artist: bool = True,
    show_album: bool = True,
    show_music: bool = True,
    show_words: bool = True,
    show_tab: bool = True,
    show_copyright: bool = True,
    line_length: int = 60,
    show_lyrics: bool = True,
    show_bar_numbers: bool = True,
    split_sections: bool = True,
    lyrics_position: LyricsPosition = LyricsPosition.Top,
):
    with gp_path.open("rb") as stream:
        song = guitarpro.parse(stream)

    config = RenderConfig(
        HeaderConfig(
            show_title=show_title,
            center_title=center_title,
            show_subtitle=show_subtitle,
            show_artist=show_artist,
            show_album=show_album,
            show_music=show_music,
            show_words=show_words,
            show_tab=show_tab,
            show_copyright=show_copyright,
        ),
        LineConfig(
            line_length=line_length,
            show_lyrics=show_lyrics,
            show_bar_numbers=show_bar_numbers,
            lyrics_position=lyrics_position,
            split_sections=split_sections,
        ),
    )

    rendered_song = render_song(song, config=config, track_number=track_number)

    if out_path:
        with out_path.open("w") as f:
            f.write(rendered_song)
    else:
        print(rendered_song)


if __name__ == "__main__":
    typer.run(main)
