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
    track = song.tracks[track_number]

    for measure in track.measures:
        beats = get_measure_beats(measure)
