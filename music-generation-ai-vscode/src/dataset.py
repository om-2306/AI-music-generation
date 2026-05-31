from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
from music21 import chord, converter, note

EOS_TOKEN = "<EOS>"


def discover_midi_files(data_dir: str | Path) -> list[Path]:
    """Return MIDI files below data_dir in a stable order."""
    root = Path(data_dir)
    patterns = ("*.mid", "*.midi")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(root.rglob(pattern))
    return sorted(files)


def _duration(element: note.Note | note.Rest | chord.Chord) -> str:
    return f"{float(element.quarterLength):.2f}"


def element_to_token(element: object) -> str | None:
    if isinstance(element, note.Note):
        return f"N:{element.pitch.nameWithOctave}:{_duration(element)}"
    if isinstance(element, chord.Chord):
        pitches = ".".join(pitch.nameWithOctave for pitch in element.pitches)
        return f"C:{pitches}:{_duration(element)}"
    if isinstance(element, note.Rest):
        return f"R:REST:{_duration(element)}"
    return None


def parse_midi_file(path: str | Path) -> list[str]:
    """Convert one MIDI file into note/chord/rest tokens."""
    midi = converter.parse(str(path))
    elements = midi.flatten().notesAndRests

    tokens: list[str] = []
    for element in elements:
        token = element_to_token(element)
        if token is not None:
            tokens.append(token)
    return tokens


def load_token_stream(data_dir: str | Path) -> list[str]:
    files = discover_midi_files(data_dir)
    if not files:
        raise FileNotFoundError(
            f"No MIDI files found in {Path(data_dir).resolve()}. "
            "Add .mid/.midi files or run src/make_demo_midi.py."
        )

    stream: list[str] = []
    failures: list[str] = []
    for path in files:
        try:
            tokens = parse_midi_file(path)
        except Exception as exc:  # music21 can fail on malformed MIDI files.
            failures.append(f"{path.name}: {exc}")
            continue

        if tokens:
            stream.extend(tokens)
            stream.append(EOS_TOKEN)

    if not stream:
        detail = "\n".join(failures[:5])
        raise ValueError(f"No usable tokens were parsed from MIDI files.\n{detail}")

    if failures:
        print("Skipped malformed MIDI files:")
        for failure in failures[:10]:
            print(f"  - {failure}")

    return stream


def build_vocabulary(tokens: Iterable[str]) -> tuple[dict[str, int], dict[int, str]]:
    vocabulary = sorted(set(tokens))
    token_to_int = {token: idx for idx, token in enumerate(vocabulary)}
    int_to_token = {idx: token for token, idx in token_to_int.items()}
    return token_to_int, int_to_token


def prepare_sequences(
    tokens: list[str],
    sequence_length: int,
    token_to_int: dict[str, int] | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, int], dict[int, str]]:
    if len(tokens) <= sequence_length:
        raise ValueError(
            f"Need more than {sequence_length} tokens, but only found {len(tokens)}."
        )

    if token_to_int is None:
        token_to_int, int_to_token = build_vocabulary(tokens)
    else:
        int_to_token = {idx: token for token, idx in token_to_int.items()}

    encoded = [token_to_int[token] for token in tokens]
    inputs = []
    targets = []
    for index in range(0, len(encoded) - sequence_length):
        inputs.append(encoded[index : index + sequence_length])
        targets.append(encoded[index + sequence_length])

    x = np.asarray(inputs, dtype=np.int32)
    y = np.asarray(targets, dtype=np.int32)
    return x, y, token_to_int, int_to_token


def save_json(path: str | Path, payload: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))
