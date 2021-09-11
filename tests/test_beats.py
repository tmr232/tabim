import re
from collections import deque
from itertools import groupby
from operator import attrgetter
from typing import Iterable, Any, Optional

import guitarpro


def unnest(iterable: Iterable[Any], *attrs: str, extra: Optional[str] = None):
    items = deque(iterable)

    if attrs:
        sentinel = object()
        items.append(sentinel)
        for getter in map(attrgetter, attrs):
            while items:
                item = items.popleft()
                if item is sentinel:
                    break
                items.extend(getter(item))

    if extra:
        yield from map(attrgetter(extra), items)
    else:
        yield from items


class TabBeat:
    is_measure_break: bool = False
    is_rest: bool = False


def get_measure_beats(measure: guitarpro.Measure):
    beats = unnest(measure.voices, "beats")
    return sorted(beats, key=attrgetter("start"))


def get_grouped_beats(measure: guitarpro.Measure):
    return groupby(get_measure_beats(measure), key=attrgetter("start"))


def parse_lyrics(lyric_line: guitarpro.LyricLine, track: guitarpro.Track):
    timestamps = []
    for measure in track.measures[lyric_line.startingMeasure - 1 :]:
        for beat in measure.voices[0].beats:
            if beat.status != guitarpro.BeatStatus.normal:
                continue
            timestamps.append(beat.start)

    lyric_fragments = re.split("- \n", lyric_line.lyrics)

    return dict(zip(timestamps, lyric_fragments))


def parse_song(song: guitarpro.Song, track_number: int = 0):
    """
    The idea is that we break the song up into yet another new kind of beat.
    This itme, the beat holds notes of the following types:

        * ``Play(note)`` - this is where the note starts
        * ``Cont(note)`` - The note is still active
        * ``Tie(note, into)`` - Ties to the previous note. Also holds the original note.

    So that later we can iterate and know what to render.
    Additionally, a beat can also have a "measure-bound" type so that
    we just know to draw it.

    The idea is that as we traverse the notes, we build the beats to
    hold all the relevant information.
    Later, when we actually draw - we traverse in pairs (or triplets?) to
    know how to apply effects and continuations.
    But the basic knowledge of whether to apply continuations is already present.

    Beats will also hold info on whether they are "Strong" beats (quarters in 4/4, for example)
    and the relevant lyric fragment.
    """
    track = song.tracks[track_number]

    for measure in track.measures:
        beats = get_measure_beats(measure)
