import io

import guitarpro

from tabim.song import render_song


def render_song_from_buffer(buffer):
    stream = io.BytesIO(bytes(buffer))
    song = guitarpro.parse(stream)
    return render_song(song)
