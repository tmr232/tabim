from itertools import chain
from operator import attrgetter
from typing import List, Sequence, Optional

import attr
from more_itertools import windowed

from tabim.tabim import DisplayNote


@attr.s(auto_attribs=True)
class Note:
    start: int
    end: int
    fret: int
    string: int


@attr.s(auto_attribs=True)
class StringNote:
    note: Note
    cont: bool = False
    from_cont: bool = False

    @staticmethod
    def from_note(note: Note) -> "StringNote":
        return StringNote(note=note)


@attr.s(auto_attribs=True)
class String:
    notes: List[StringNote] = attr.field(factory=list)

    def add_note(self, note: Note):
        """Notes must be added in sorted order"""
        self.notes.append(StringNote.from_note(note))

    def mark_cont(self, timestamp: int):
        for note, nxt in windowed(chain(self.notes, [None]), 2):
            # If a note started playing mid-note, we want a continuation
            if note.note.start < timestamp < note.note.end:
                note.cont = True
                # Lead into the next note
                if nxt and nxt.note.start == timestamp:
                    nxt.from_cont = True
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

    def __getitem__(self, timestamp: int):
        column = []
        for string in self.strings:
            string_note = string[timestamp]
            display_note = make_display_note(string_note, timestamp)
            column.append(display_note)

        return column


def make_display_note(string_note: Optional[StringNote], timestamp: int) -> DisplayNote:
    if not string_note:
        return DisplayNote()

    if timestamp == string_note.note.start:
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


def build_measure(notes: Sequence[Note], n_strings=6) -> Measure:
    start_times = set()
    strings = Strings(n=n_strings)
    for note in sorted(notes, key=attrgetter("start")):
        start_times.add(note.start)

        strings[note.string].add_note(note)

    for start in start_times:
        for string in strings:
            string.mark_cont(start)

    return Measure(strings=strings)
