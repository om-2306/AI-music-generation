from __future__ import annotations

import argparse
import random
import struct
from pathlib import Path

TPQ = 480


NOTE_MAP = {
    "C": 0,
    "C#": 1,
    "D": 2,
    "D#": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "G": 7,
    "G#": 8,
    "A": 9,
    "A#": 10,
    "B": 11,
}


def note_number(name: str) -> int:
    pitch = name[:-1]
    octave = int(name[-1])
    return 12 * (octave + 1) + NOTE_MAP[pitch]


def var_len(value: int) -> bytes:
    buffer = value & 0x7F
    value >>= 7
    while value:
        buffer <<= 8
        buffer |= ((value & 0x7F) | 0x80)
        value >>= 7

    result = bytearray()
    while True:
        result.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            break
    return bytes(result)


def event(delta: int, payload: bytes) -> bytes:
    return var_len(delta) + payload


def track_chunk(events: bytes) -> bytes:
    return b"MTrk" + struct.pack(">I", len(events)) + events


def header_chunk(track_count: int) -> bytes:
    return b"MThd" + struct.pack(">IHHH", 6, 1, track_count, TPQ)


def note_events(notes: list[tuple[str, float, int]], channel: int) -> bytes:
    data = bytearray()
    for pitch, beats, velocity in notes:
        number = note_number(pitch)
        ticks = int(TPQ * beats)
        data += event(0, bytes([0x90 | channel, number, velocity]))
        data += event(ticks, bytes([0x80 | channel, number, 0]))
    return bytes(data)


def chord_events(chords: list[tuple[list[str], float]], channel: int) -> bytes:
    data = bytearray()
    for chord, beats in chords:
        ticks = int(TPQ * beats)
        for index, pitch in enumerate(chord):
            data += event(0, bytes([0x90 | channel, note_number(pitch), 68]))
        for index, pitch in enumerate(chord):
            delta = ticks if index == 0 else 0
            data += event(delta, bytes([0x80 | channel, note_number(pitch), 0]))
    return bytes(data)


def meta_track(title: str, bpm: int) -> bytes:
    tempo = int(60_000_000 / bpm)
    data = bytearray()
    data += event(0, b"\xFF\x03" + var_len(len(title)) + title.encode("ascii"))
    data += event(0, b"\xFF\x51\x03" + tempo.to_bytes(3, "big"))
    data += event(0, b"\xFF\x58\x04\x04\x02\x18\x08")
    data += event(0, b"\xFF\x2F\x00")
    return track_chunk(bytes(data))


def music_track(events: bytes, instrument: int, channel: int) -> bytes:
    data = bytearray()
    data += event(0, bytes([0xC0 | channel, instrument]))
    data += events
    data += event(0, b"\xFF\x2F\x00")
    return track_chunk(bytes(data))


def write_midi(path: Path, title: str, bpm: int, melody: list[tuple[str, float, int]], chords: list[tuple[list[str], float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = bytearray()
    content += header_chunk(3)
    content += meta_track(title, bpm)
    content += music_track(note_events(melody, channel=0), instrument=0, channel=0)
    content += music_track(chord_events(chords, channel=1), instrument=0, channel=1)
    path.write_bytes(bytes(content))


PROGRESSIONS = {
    "bright_classical": [
        ["C3", "E3", "G3"],
        ["G3", "B3", "D4"],
        ["A3", "C4", "E4"],
        ["F3", "A3", "C4"],
    ],
    "minor_cinematic": [
        ["A2", "C3", "E3"],
        ["F2", "A2", "C3"],
        ["C3", "E3", "G3"],
        ["G2", "B2", "D3"],
    ],
    "jazz_ii_v_i": [
        ["D3", "F3", "A3", "C4"],
        ["G2", "B2", "D3", "F3"],
        ["C3", "E3", "G3", "B3"],
        ["A2", "C3", "E3", "G3"],
    ],
    "waltz": [
        ["C3", "E3", "G3"],
        ["F3", "A3", "C4"],
        ["G3", "B3", "D4"],
        ["C3", "E3", "G3"],
    ],
}

SCALES = {
    "bright_classical": ["C4", "D4", "E4", "G4", "A4", "C5"],
    "minor_cinematic": ["A3", "B3", "C4", "E4", "G4", "A4"],
    "jazz_ii_v_i": ["D4", "E4", "F4", "G4", "A4", "B4", "C5"],
    "waltz": ["C4", "E4", "G4", "A4", "B4", "C5"],
}


def build_song(style: str, index: int) -> tuple[int, list[tuple[str, float, int]], list[tuple[list[str], float]]]:
    rng = random.Random(1000 + index)
    bpm = {"bright_classical": 112, "minor_cinematic": 78, "jazz_ii_v_i": 132, "waltz": 92}[style]
    progression = PROGRESSIONS[style]
    scale = SCALES[style]
    melody: list[tuple[str, float, int]] = []
    chords: list[tuple[list[str], float]] = []

    for repeat in range(4):
        for chord_index, chord in enumerate(progression):
            duration = 3.0 if style == "waltz" else 2.0
            chords.append((chord, duration))
            note_count = 3 if style == "waltz" else 4
            for step in range(note_count):
                if step == note_count - 1 and repeat % 2 == 0:
                    pitch = scale[(chord_index + repeat + 2) % len(scale)]
                    beats = 1.0
                else:
                    pitch = rng.choice(scale)
                    beats = 0.5 if style != "waltz" else 1.0
                melody.append((pitch, beats, rng.randint(70, 96)))

    return bpm + index % 7, melody, chords


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create sample MIDI files without third-party dependencies.")
    parser.add_argument("--output", default="data/raw")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = Path(args.output)
    styles = ["bright_classical", "minor_cinematic", "jazz_ii_v_i", "waltz"]

    count = 0
    for index in range(12):
        style = styles[index % len(styles)]
        bpm, melody, chords = build_song(style, index)
        path = output / f"sample_{index + 1:02d}_{style}.mid"
        write_midi(path, f"Sample {index + 1} {style}", bpm, melody, chords)
        print(f"Wrote {path}")
        count += 1

    print(f"Created {count} MIDI files in {output.resolve()}")


if __name__ == "__main__":
    main()
