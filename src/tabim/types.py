from __future__ import annotations

from typing import Optional, Sequence

import attr
import guitarpro


@attr.s(auto_attribs=True)
class TabNote:
    note: guitarpro.Note
    prev_note: Optional[TabNote]
    is_play: bool = False
    is_cont: bool = False
    tie_note: Optional[TabNote] = None

    @property
    def fret(self):
        cur = self
        while cur.tie_note:
            cur = cur.tie_note
        return cur.note.value

    @property
    def is_tie(self):
        return bool(self.tie_note)

    @staticmethod
    def play(
        note: guitarpro.Note, prev_note: Optional[guitarpro.Note] = None
    ) -> TabNote:
        return TabNote(
            note=note,
            is_play=True,
            prev_note=prev_note,
        )

    @staticmethod
    def cont(
        note: guitarpro.Note, prev_note: Optional[guitarpro.Note] = None
    ) -> TabNote:
        return TabNote(
            note=note,
            is_cont=True,
            prev_note=prev_note,
        )

    @staticmethod
    def tie(
        note: guitarpro.Note,
        tie_note: TabNote,
    ) -> TabNote:
        # Propagate cont
        return TabNote(
            note=note,
            tie_note=tie_note,
            is_cont=tie_note.is_cont,
            prev_note=tie_note,
        )

    def set_cont(self):
        self.is_cont = True

        # Propagate up tie-notes!
        tie_note = self.tie_note
        while tie_note:
            tie_note.is_cont = True
            tie_note = tie_note.tie_note


@attr.s(auto_attribs=True)
class TabBeat:
    start: int
    notes: list[TabNote] = attr.Factory(list)
    is_measure_break: bool = False
    is_rest: bool = False
    lyric: str = ""

    @staticmethod
    def from_notes(
        start: int, notes: list[TabNote], lyric: Optional[str] = None
    ) -> TabBeat:
        return TabBeat(notes=notes, lyric=lyric, start=start)

    @staticmethod
    def measure(start: int) -> TabBeat:
        return TabBeat(is_measure_break=True, start=start)


@attr.s(auto_attribs=True, slots=True)
class AsciiMeasure:
    lyrics: Sequence[str]
    strings: Sequence[Sequence[str]]

    @property
    def width(self):
        return len("".join(self.lyrics))

    def __len__(self):
        return self.width


@attr.s(auto_attribs=True)
class AsciiNote:
    note: str = ""
    start: int = 0

    @property
    def head(self):
        return self.note[: self.start]

    @property
    def tail(self):
        return self.note[self.start :]
