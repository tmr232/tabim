import io

import guitarpro

from tabim.song import render_song


def parse_song_from_buffer(buffer) -> guitarpro.Song:
    stream = io.BytesIO(bytes(buffer))
    song = guitarpro.parse(stream)
    return song


def render_song_from_buffer(buffer) -> str:
    song = parse_song_from_buffer(buffer)
    return render_song(song)
