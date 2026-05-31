from __future__ import annotations

import argparse
import random
from pathlib import Path

from music21 import chord, instrument, key, meter, note, stream, tempo


PROGRESSIONS = [
    ["C", "G", "Am", "F"],
    ["Dm", "G", "C", "C"],
    ["Am", "F", "C", "G"],
    ["F", "G", "Em", "Am"],
]

CHORD_PITCHES = {
    "C": ["C3", "E3", "G3"],
    "Dm": ["D3", "F3", "A3"],
    "Em": ["E3", "G3", "B3"],
    "F": ["F3", "A3", "C4"],
    "G": ["G3", "B3", "D4"],
    "Am": ["A3", "C4", "E4"],
}

MELODY_POOL = {
    "C": ["C4", "D4", "E4", "G4", "A4"],
    "Dm": ["D4", "E4", "F4", "A4", "C5"],
    "Em": ["E4", "G4", "A4", "B4", "D5"],
    "F": ["F4", "G4", "A4", "C5", "D5"],
    "G": ["G4", "A4", "B4", "D5", "E5"],
    "Am": ["A4", "B4", "C5", "E5", "G5"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a small synthetic MIDI dataset.")
    parser.add_argument("--output", default="data/raw")
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def build_piece(index: int) -> stream.Score:
    score = stream.Score()
    score.append(tempo.MetronomeMark(number=90 + (index % 5) * 8))
    score.append(meter.TimeSignature("4/4"))
    score.append(key.Key("C"))

    harmony = stream.Part()
    harmony.insert(0, instrument.Piano())
    melody = stream.Part()
    melody.insert(0, instrument.Piano())

    progression = PROGRESSIONS[index % len(PROGRESSIONS)]
    for _ in range(4):
        for symbol in progression:
            harmony.append(chord.Chord(CHORD_PITCHES[symbol], quarterLength=2.0))
            for _ in range(2):
                pitch_name = random.choice(MELODY_POOL[symbol])
                duration = random.choice([0.5, 0.5, 1.0])
                melody.append(note.Note(pitch_name, quarterLength=duration))
                if duration == 0.5:
                    melody.append(note.Rest(quarterLength=0.5))

    score.insert(0, harmony)
    score.insert(0, melody)
    return score


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    for index in range(args.count):
        piece = build_piece(index)
        path = output_dir / f"demo_{index + 1:02d}.mid"
        piece.write("midi", fp=str(path))
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
