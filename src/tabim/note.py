from __future__ import annotations

from itertools import chain
from operator import attrgetter
from typing import Optional

import guitarpro
from more_itertools import windowed

from tabim.types import AsciiNote


def render_note(
    note: Optional[guitarpro.Note],
    prev: Optional[guitarpro.Note],
) -> AsciiNote:
    if not note:
        return AsciiNote()
    if note.type == guitarpro.NoteType.normal:
        if prev and prev.effect.hammer:
            if prev.value > note.value:
                return AsciiNote(f"p{note.value}", 1)
            else:
                return AsciiNote(f"h{note.value}", 1)

        if note.effect.isHarmonic:
            if isinstance(note.effect.harmonic, guitarpro.NaturalHarmonic):
                return AsciiNote(f"<{note.value}>", 1)

        if prev and prev.effect.slides:
            if prev.effect.slides[0] == guitarpro.SlideType.legatoSlideTo:
                if prev.value > note.value:
                    return AsciiNote(f"\\{note.value}", 1)
                else:
                    return AsciiNote(f"/{note.value}", 1)
            if prev.effect.slides[0] == guitarpro.SlideType.shiftSlideTo:
                return AsciiNote(f"s{note.value}", 1)

        if note.effect.isBend:
            bend = note.effect.bend
            if bend.type in (guitarpro.BendType.bend, guitarpro.BendType.bendRelease):
                parts = [f"{note.value}"]
                for frm, to in windowed(
                    chain([0], map(attrgetter("value"), bend.points)), 2
                ):
                    if frm < to:
                        parts.append(f"b{note.value + to // 2}")
                    elif frm > to:
                        parts.append(f"r{note.value + to // 2}")
                return AsciiNote("".join(parts), 0)

        if note.effect.isTrill:
            return AsciiNote(f"{note.value}tr{note.effect.trill.fret}")

        if note.effect.vibrato:
            return AsciiNote(f"{note.value}~")

        if note.effect.isDefault or note.effect.hammer or note.effect.slides:
            # Hammers affect the _next_ note.
            # Same goes for slides
            return AsciiNote(f"{note.value}")

    if note.type == guitarpro.NoteType.tie:
        if prev:
            return AsciiNote(f"({prev.value})", 1)

    if note.type == guitarpro.NoteType.rest:
        return AsciiNote()

    if note.type == guitarpro.NoteType.dead:
        return AsciiNote("x")

    raise NotImplementedError()
