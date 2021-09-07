from itertools import chain
from operator import attrgetter
from typing import List, Sequence, Optional, Iterator

import attr
import guitarpro.models
from more_itertools import windowed

from tabim.render import DisplayNote


@attr.frozen
class Note:
    gp_note: guitarpro.models.Note

    @property
    def beat(self):
        return self.gp_note.beat

    @property
    def start(self):
        return self.beat.startInMeasure

    @property
    def end(self):
        return self.beat.startInMeasure + self.beat.duration.time

    @property
    def fret(self):
        return self.gp_note.value

    @property
    def string(self):
        return self.gp_note.string

    @property
    def tie(self):
        return self.gp_note.type == guitarpro.models.NoteType.tie


@attr.s(auto_attribs=True)
class StringNote:
    note: Note
    cont: bool = False
    from_cont: bool = False

    @staticmethod
    def from_note(note: Note) -> "StringNote":
        return StringNote(note=note, from_cont=note.tie, cont=note.tie)


@attr.s(auto_attribs=True)
class String:
    notes: List[StringNote] = attr.field(factory=list)

    def add_note(self, note: Note):
        """Notes must be added in sorted order"""
        self.notes.append(StringNote.from_note(note))

    def mark_cont(self, timestamp: int):
        cur = None
        for note, nxt in windowed(chain(self.notes, [None]), 2):
            if not note:
                continue
            if not note.note.tie:
                cur = note
            # If a note started playing mid-note, we want a continuation
            if note.note.tie and note.note.start == timestamp:
                # Also consider anything that starts on a tie-note
                note.cont = True
                note.from_cont = True
                if cur:
                    cur.cont = True
                return
            if note.note.start < timestamp < note.note.end:
                note.cont = True
                # Lead into the next note
                if nxt and nxt.note.start == timestamp:
                    nxt.from_cont = True

                if note.note.tie:
                    if cur:
                        cur.cont = True
                return

    def __getitem__(self, timestamp: int):
        for note in self.notes:
            if note.note.start <= timestamp < note.note.end:
                return note
        return None


class Strings:
    def __init__(self, n: int = 6):
        self.strings = [String() for _ in range(n)]

    def __getitem__(self, string: int):
        return self.strings[string - 1]

    def __iter__(self):
        yield from self.strings

    def __len__(self):
        return len(self.strings)


@attr.s(auto_attribs=True)
class Measure:
    strings: Strings
    timestamps: Sequence[int]

    def __getitem__(self, timestamp: int):
        column = []
        for string in self.strings:
            string_note = string[timestamp]
            display_note = make_display_note(string_note, timestamp)
            column.append(display_note)

        return column

    @property
    def columns(self):
        for timestamp in self.timestamps:
            yield self[timestamp]


def make_display_note(string_note: Optional[StringNote], timestamp: int) -> DisplayNote:
    if not string_note:
        return DisplayNote()

    if timestamp == string_note.note.start and not string_note.note.tie:
        return DisplayNote(
            cont_in=string_note.from_cont,
            cont_out=string_note.cont,
            fret=string_note.note.fret,
        )

    return DisplayNote(
        cont_in=string_note.cont,
        cont_out=string_note.cont,
        cont=string_note.cont,
        fret=string_note.note.fret,
    )


def parse_notes(measure: guitarpro.models.Measure) -> Sequence[Note]:
    notes = []

    for voice in measure.voices:
        for beat in voice.beats:
            for note in beat.notes:
                notes.append(Note(gp_note=note))
    return sorted(notes, key=attrgetter("start"))


def build_measure(notes: Sequence[Note], n_strings=6) -> Measure:
    start_times = set()
    strings = Strings(n=n_strings)
    for note in sorted(notes, key=attrgetter("start")):
        if not note.tie:
            start_times.add(note.start)

        strings[note.string].add_note(note)

    for start in start_times:
        for string in strings:
            string.mark_cont(start)

    return Measure(strings=strings, timestamps=sorted(start_times))
