from __future__ import annotations

import io
import re
from functools import reduce
from itertools import chain, groupby, repeat
from operator import attrgetter
from typing import Iterator, Optional, Sequence

import guitarpro
from more_itertools import chunked, interleave

from tabim.config import LyricsPosition, RenderConfig
from tabim.note import render_note
from tabim.types import AsciiMeasure, TabBeat, TabNote
from tabim.utils import concat_columns, strip_trailing_whitespace, try_getattr, unnest


def get_measure_beats(measure: guitarpro.Measure) -> list[guitarpro.Beat]:
    beats = unnest(measure.voices, "beats")
    return sorted(beats, key=attrgetter("start"))


def get_grouped_beats(
    measure: guitarpro.Measure,
) -> Iterator[tuple[int, Iterator[guitarpro.Beat]]]:
    return groupby(get_measure_beats(measure), key=attrgetter("start"))  # type:ignore


def parse_lyrics(
    lyric_line: guitarpro.LyricLine, track: guitarpro.Track
) -> dict[int, str]:
    timestamps = []
    for measure in track.measures[lyric_line.startingMeasure - 1 :]:
        for beat in measure.voices[0].beats:
            if beat.status != guitarpro.BeatStatus.normal:
                continue
            timestamps.append(beat.start)

    lyric_fragments = [
        "".join(parts).strip()
        for parts in chunked(re.split("([- \n]+)", lyric_line.lyrics), 2)
    ]

    return dict(zip(timestamps, lyric_fragments))


def parse_song(song: guitarpro.Song, track_number: int = 0) -> Sequence[TabBeat]:
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

    lyric_timestamps = parse_lyrics(song.lyrics.lines[0], track)

    tab_beats = []
    live_notes: list[Optional[TabNote]] = [None for _ in track.strings]
    for measure in track.measures:
        for timestamp, beats in get_grouped_beats(measure):
            tie_live_notes = live_notes[:]
            # Remove all ended live-notes
            for string, note in enumerate(live_notes):
                if not note:
                    continue
                if note.note.beat.start + note.note.beat.duration.time <= timestamp:
                    live_notes[string] = None

            # Collect new notes from current beats
            notes: list[Optional[TabNote]] = [None for _ in track.strings]
            new_live_notes = live_notes[:]
            tie_notes = []
            has_play = False  # Denotes whether any play-note was present in the beat
            for beat in beats:
                for note in beat.notes:
                    if note.type == guitarpro.NoteType.tie:
                        new_note = TabNote.tie(
                            note, tie_note=tie_live_notes[note.string - 1]
                        )
                        tie_notes.append(new_note)
                    else:
                        new_note = TabNote.play(
                            note, prev_note=tie_live_notes[note.string - 1]
                        )
                        has_play = True
                    new_live_notes[note.string - 1] = new_note
                    notes[note.string - 1] = new_note
            if has_play:
                for tie_note in tie_notes:
                    tie_note.set_cont()

            # Mark continuation for live notes
            for string, (note, live_note) in enumerate(zip(notes, live_notes)):
                if note:
                    continue
                if live_note and has_play:
                    notes[string] = TabNote.cont(
                        live_note.note, tie_live_notes[live_note.note.string - 1]
                    )
                    # Propagate cont
                    live_note.set_cont()

            # Update live notes
            live_notes = new_live_notes

            tab_beats.append(
                TabBeat.from_notes(
                    notes=notes,
                    lyric=lyric_timestamps.get(timestamp, ""),
                    start=timestamp,
                )
            )

        tab_beats.append(TabBeat.measure(start=measure.end))

    return tab_beats


def less_naive_render_beats(
    beats: Sequence[TabBeat], n_strings: int = 6
) -> Sequence[AsciiMeasure]:
    lyrics = []
    strings = [[] for _ in range(n_strings)]

    measures: list[AsciiMeasure] = []

    measure_break_notes = [True for _ in range(n_strings)]
    first_beat_in_measure = True

    for beat in beats:
        if beat.is_measure_break:
            measures.append(AsciiMeasure(lyrics=lyrics, strings=strings))
            lyrics = []
            strings = [[] for _ in range(n_strings)]
            measure_break_notes = [True for _ in range(n_strings)]
            first_beat_in_measure = True
            continue

        ascii_notes = [
            render_note(
                note=try_getattr(note, "note"),
                prev=try_getattr(note, "prev_note.note"),
            )
            for note in beat.notes
        ]

        max_head = max(len(note.head) for note in ascii_notes)
        max_tail = max(
            len(beat.lyric),
            max(len(note.tail) for note in ascii_notes),
        )

        draw_width = max(3, max_head + max_tail + 1)
        draw_tail = draw_width - max_head

        lyrics.append(" " * max_head + beat.lyric.ljust(draw_tail))
        for i, (note, ascii_note) in enumerate(zip(beat.notes, ascii_notes)):
            # No note, so we just draw the empty state
            if not note:
                strings[i].append("-" * (draw_width + int(first_beat_in_measure)))
                continue

            # If the previous note is a cont, we need to pad with a cont
            head_pad = "-"
            if note.prev_note and note.prev_note.is_cont:
                head_pad = "="

            # If this is a cont, pad with a cont
            tail_pad = "-"
            if note.is_cont:
                tail_pad = "="

            base = ""
            head = 0
            tail = 0
            if note.is_play or (note.is_tie and measure_break_notes[i]):
                base = ascii_note.note
                head = len(ascii_note.head)
                tail = len(ascii_note.tail)

            rendered = (
                head_pad * (max_head - head) + base + tail_pad * (draw_tail - tail)
            )

            if first_beat_in_measure:
                rendered = head_pad + rendered

            measure_break_notes[i] = False

            strings[i].append(rendered)

        first_beat_in_measure = False

    return measures


def render_measure(
    measure: AsciiMeasure,
    show_lyrics: bool = True,
    lyrics_position: LyricsPosition = LyricsPosition.Top,
) -> str:
    output = io.StringIO()

    def add_lyrics():
        if show_lyrics:
            print("".join(measure.lyrics), file=output)

    if lyrics_position == LyricsPosition.Top:
        add_lyrics()

    for string in measure.strings:
        print("".join(string), file=output)

    if lyrics_position == LyricsPosition.Bottom:
        add_lyrics()

    return output.getvalue()


def render_line(
    line: Sequence[AsciiMeasure],
    tuning: Sequence[str],
    show_lyrics: bool = True,
    lyrics_position: LyricsPosition = LyricsPosition.Top,
    n_string: int = 6,
) -> str:
    rendered_measures = [
        render_measure(
            measure, show_lyrics=show_lyrics, lyrics_position=lyrics_position
        )
        for measure in line
    ]

    if show_lyrics:
        if lyrics_position == LyricsPosition.Top:
            tuning_header = "\n".join([" "] + list(tuning))
            measure_separator = "\n".join(" " + "|" * n_string)
        else:  # lyrics_position == LyricsPosition.Bottom:
            tuning_header = "\n".join(list(tuning) + [" "])
            measure_separator = "\n".join("|" * n_string + " ")

    else:
        tuning_header = "\n".join(list(tuning))
        measure_separator = "\n".join("|" * n_string)

    return reduce(
        concat_columns,
        chain(
            [tuning_header],
            interleave(repeat(measure_separator), rendered_measures),
            [measure_separator],
        ),
    )


def render_measures(
    measures: Sequence[AsciiMeasure],
    line_length: int = 90,
    tuning: Sequence[str] = "EADGBe"[::-1],
    show_lyrics: bool = True,
    bar_numbers: bool = True,
    lyrics_position: LyricsPosition = LyricsPosition.Top,
) -> str:

    lines = []
    current_line = []
    current_line_length = 0
    for measure in measures:
        current_line.append(measure)
        current_line_length += len(measure)
        if current_line_length > line_length:
            lines.append(current_line)
            current_line = []
            current_line_length = 0

    lines.append(current_line)

    current_bar = 1
    output = io.StringIO()
    for line in lines:
        rendered_line = render_line(
            line,
            show_lyrics=show_lyrics,
            tuning=tuning,
            lyrics_position=lyrics_position,
        )

        if bar_numbers:
            print(current_bar, file=output)

            if lyrics_position == LyricsPosition.Bottom or not show_lyrics:
                print(file=output)

        print(rendered_line, file=output)
        print(file=output)

        current_bar += len(line)

    return strip_trailing_whitespace(output.getvalue())


def get_tuning(strings: Sequence[guitarpro.GuitarString]):
    tuning = []
    notes = "C C# D D# E F F# G G# A A# B".split()
    for string in strings:
        octave, semitone = divmod(string.value, 12)
        tuning.append(notes[semitone])

    max_width = max(map(len, tuning))
    tuning = [n.ljust(max_width) for n in tuning]
    return tuning


def render_song(
    song: guitarpro.Song,
    track_number: int = 0,
    config: Optional[RenderConfig] = None,
) -> str:
    if config is None:
        config = RenderConfig()

    tab = parse_song(song, track_number)
    measures = less_naive_render_beats(
        tab, n_strings=len(song.tracks[track_number].strings)
    )
    tuning = get_tuning(song.tracks[track_number].strings)
    body = render_measures(
        measures,
        line_length=config.line.line_length,
        show_lyrics=config.line.show_lyrics,
        bar_numbers=config.line.show_bar_numbers,
        tuning=tuning,
        lyrics_position=config.line.lyrics_position,
    )

    header_lines = []

    if config.header.show_title and song.title:
        if config.header.center_title:
            header_lines.append(song.title.center(config.line.line_length))
        else:
            header_lines.append(song.title)

        header_lines.append("")

    if config.header.show_subtitle and song.subtitle:
        if config.header.center_title:
            header_lines.append(song.subtitle.center(config.line.line_length))
        else:
            header_lines.append(song.subtitle)

        header_lines.append("")

    if config.header.show_album and song.album:
        header_lines.append(f"Album: {song.album}")

    if config.header.show_artist and song.artist:
        header_lines.append(f"Artist: {song.artist}")

    if config.header.show_music and song.music:
        header_lines.append(f"Music: {song.music}")

    if config.header.show_words and song.words:
        header_lines.append(f"Words: {song.words}")

    if config.header.show_copyright and song.copyright:
        header_lines.append(f"Copyright: {song.copyright}")

    if config.header.show_tab and song.tab:
        header_lines.append(f"Arrangement: {song.tab}")

    header = "\n".join(header_lines)

    output = io.StringIO()

    print(header, file=output)
    print(file=output)
    print(body, file=output)

    return strip_trailing_whitespace(output.getvalue())
