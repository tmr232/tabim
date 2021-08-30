from typing import List, Dict

import attr
import guitarpro
from tests.conftest import get_sample
import rich

def test_basic():
    with open(get_sample("OneWholeBar.gp5"), 'rb') as stream:
        tab = guitarpro.parse(stream)

    assert tab.title == "One Whole Bar"

    track = tab.tracks[0]
    bar = track.measures[0]
    voice = bar.voices[0]
    beat = voice.beats[0]
    print(beat.notes)

def test_different_notes():
    with open(get_sample("DifferentNotes.gp5"), 'rb') as stream:
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

@attr.mutable
class AsciiBeat:
    notes:Dict[int, int] = attr.field(factory=dict)

    def add_note(self, string:int, fret:int):
        self.notes[string] = fret

@attr.mutable
class AsciiMeasure:
    beats:List[AsciiBeat] = attr.field(factory=list)

    def add_beat(self, beat:AsciiBeat):
        self.beats.append(beat)

    def render(self):
        cols = []
        cols.append(reversed("EADGBe"))
        cols.append(["|"]*6)
        cols.append(["-"]*6)
        for beat in self.beats:
            notes = [str(beat.notes.get(string, '-')) for string in range(1,7)]
            cols.append(notes)
            cols.append(["-"]*6)

        cols.append(["|"] * 6)

        rows = map(list, zip(*cols))

        return "\n".join("".join(row) for row in rows)

def format_measure(measure:guitarpro.models.Measure):
    ascii = AsciiMeasure()
    voice = measure.voices[0]

    for beat in voice.beats:
        ascii_beat = AsciiBeat()

        for note in beat.notes:
            ascii_beat.add_note(string=note.string, fret=note.value)
        ascii.add_beat(ascii_beat)

    return ascii.render()

def print_measure(measure:guitarpro.models.Measure):
    print(format_measure(measure))
    print()

def test_basic_rendering():
    with open(get_sample("DifferentNotes.gp5"), 'rb') as stream:
        tab = guitarpro.parse(stream)

    track = tab.tracks[0]

    for measure in track.measures:
        print_measure(measure)