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