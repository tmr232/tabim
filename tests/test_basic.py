import enum
import heapq
from itertools import chain, groupby
from operator import attrgetter, itemgetter
from typing import List, Dict, Set, Sequence, Iterator
from more_itertools import windowed
import attr
import guitarpro
from tests.conftest import get_sample
import rich


def test_basic():
    with open(get_sample("OneWholeBar.gp5"), "rb") as stream:
        tab = guitarpro.parse(stream)

    assert tab.title == "One Whole Bar"

    track = tab.tracks[0]
    bar = track.measures[0]
    voice = bar.voices[0]
    beat = voice.beats[0]
    print(beat.notes)


def test_different_notes():
    with open(get_sample("DifferentNotes.gp5"), "rb") as stream:
        tab = guitarpro.parse(stream)

    for track in tab.tracks:
        for measure in track.measures:
            for voice in measure.voices:
                for beat in voice.beats:
                    rich.print(beat)
                    # for note in beat.notes:
                    #     rich.print(note)

    track = tab.tracks[0]
    bar = track.measures[0]
    voice = bar.voices[0]
    beat = voice.beats[0]
    print(beat.notes)
    print(len(tab.tracks[0].measures))
    print(beat.startInMeasure)


@attr.mutable
class AsciiBeat:
    notes: Dict[int, int] = attr.field(factory=dict)

    def add_note(self, string: int, fret: int):
        self.notes[string] = fret


@attr.mutable
class AsciiMeasure:
    beats: List[AsciiBeat] = attr.field(factory=list)

    def add_beat(self, beat: AsciiBeat):
        self.beats.append(beat)

    def render(self):
        cols = []
        cols.append(reversed("EADGBe"))
        cols.append(["|"] * 6)
        cols.append(["-"] * 6)
        for beat in self.beats:
            notes = [str(beat.notes.get(string, "-")) for string in range(1, 7)]
            cols.append(notes)
            cols.append(["-"] * 6)

        cols.append(["|"] * 6)

        rows = map(list, zip(*cols))

        return "\n".join("".join(row) for row in rows)


@attr.frozen
class Note:
    start: int
    end: int
    string: int
    fret: int


class Action(enum.IntEnum):
    # The numbering is an ordering hack...
    STOP = 0
    PLAY = 1


@attr.frozen
class Event:
    timestamp: int
    action: Action
    note: Note = attr.ib(order=False)


@attr.frozen
class EventGroup:
    timestamp: int
    events: Sequence[Event]


def group_events(events: Sequence[Event]) -> Iterator[EventGroup]:
    for timestamp, grouped_events in groupby(events, key=attrgetter("timestamp")):
        yield EventGroup(timestamp=timestamp, events=tuple(grouped_events))


@attr.mutable
class Measure:
    length: int
    notes: List[Note] = attr.field(factory=list)

    def get_events(self) -> Sequence[Event]:
        events = []
        for note in self.notes:
            events.append(Event(timestamp=note.start, action=Action.PLAY, note=note))
            events.append(Event(timestamp=note.end, action=Action.STOP, note=note))

        events.sort(key=attrgetter("timestamp"))

        return events


def render_measure(measure: Measure) -> str:
    strings = {n: "" for n in range(1, 6 + 1)}
    curr = {n: None for n in range(1, 6 + 1)}
    prev = {n: None for n in range(1, 6 + 1)}
    for beat in group_events(measure.get_events()):
        for event in (event for event in beat.events if event.action == Action.STOP):
            curr[event.note.string] = None
        for event in (event for event in beat.events if event.action == Action.PLAY):
            curr[event.note.string] = event.note.fret

        for string in strings:
            if curr[string] is None:
                strings[string] += "-"
            elif curr[string] == prev[string]:
                strings[string] += "="
            else:
                strings[string] += str(curr[string])

        prev = curr.copy()

    return "\n".join(
        f"|-{string}-|" for _, string in sorted(strings.items(), key=itemgetter(0))
    )


def measure_from_gp(gp_measure: guitarpro.models.Measure):
    measure = Measure(length=gp_measure.length)

    for voice in gp_measure.voices:
        for beat in voice.beats:
            for gp_note in beat.notes:
                note = Note(
                    start=beat.startInMeasure,
                    end=beat.startInMeasure + beat.duration.time,
                    fret=gp_note.value,
                    string=gp_note.string,
                )
                measure.notes.append(note)

    return measure


def format_measure(measure: guitarpro.models.Measure):
    ascii = AsciiMeasure()
    voice = measure.voices[0]

    for beat in voice.beats:
        ascii_beat = AsciiBeat()

        for note in beat.notes:
            ascii_beat.add_note(string=note.string, fret=note.value)
        ascii.add_beat(ascii_beat)

    return ascii.render()


def print_measure(measure: guitarpro.models.Measure):
    print(format_measure(measure))
    print()


def test_basic_rendering():
    with open(get_sample("DifferentNotes.gp5"), "rb") as stream:
        tab = guitarpro.parse(stream)

    track = tab.tracks[0]

    for measure in track.measures:
        print_measure(measure)


def test_measure_conversion():
    with open(get_sample("DifferentNotes.gp5"), "rb") as stream:
        tab = guitarpro.parse(stream)

    track = tab.tracks[0]

    for gp_measure in track.measures:
        measure = measure_from_gp(gp_measure)
        rich.print(measure)
        print(render_measure(measure))


def test_basic_sustain():
    with open(get_sample("BasicSustain.gp5"), "rb") as stream:
        tab = guitarpro.parse(stream)

    track = tab.tracks[0]

    for gp_measure in track.measures:
        measure = measure_from_gp(gp_measure)
        rich.print(measure)
        print(render_measure(measure))


## NEW!


def iter_measure_notes(measure: guitarpro.models.Measure) -> Iterator[Note]:
    notes = []

    for voice in measure.voices:
        for beat in voice.beats:
            for note in beat.notes:
                notes.append(
                    Note(
                        start=beat.startInMeasure,
                        end=beat.startInMeasure + beat.duration.time,
                        fret=note.value,
                        string=note.string,
                    )
                )

    yield from sorted(notes, key=attrgetter("start"))


def notes_to_events(notes: Iterator[Note]) -> Iterator[Event]:
    pending: List[Note] = []  #: This is a heap!
    for note in notes:
        start = Event(timestamp=note.start, action=Action.START, note=note)
        stop = Event(timestamp=note.end, action=Action.STOP, note=note)
        heapq.heappush(pending, stop)
        while pending and pending[0] < start:
            yield heapq.heappop(pending)
        yield start

    while pending:
        yield heapq.heappop(pending)


@attr.frozen
class StringState:
    fret: int
    continuation: bool


@attr.frozen
class Beat:
    timestamp: int
    strings: Dict[int, StringState] = attr.field(
        factory=lambda: {i + 1: None for i in range(6)}
    )


def events_to_beats(events: Iterator[Event]) -> Iterator[Beat]:
    prev = Beat(timestamp=0)
    for timestamp, grouped_events in groupby(events, key=attrgetter("timestamp")):
        strings = {i + 1: None for i in range(6)}
        for event in grouped_events:
            strings[event.note.string] = StringState(event.note.fret)


# Maybe we should divide the notes into the division for the measure.
# So in 4/4 we divide into 4 and give every quarter an equal (starting) length.
# In 3/4 we divide into 3, and so on.


def render_beats(beats: Iterator[Beat]) -> str:
    quarter_length = 960
    for prv, cur, nxt in windowed(chain([None], beats, [None]), 3):
        pass
