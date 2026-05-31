from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
from music21 import chord, note, stream, tempo
from tensorflow import keras

from dataset import EOS_TOKEN, load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate music from a trained LSTM.")
    parser.add_argument("--artifacts-dir", default="artifacts")
    parser.add_argument("--output", default="generated/generated_music.mid")
    parser.add_argument("--notes", type=int, default=200, help="Number of tokens to generate.")
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--seed-index", type=int, default=None)
    return parser.parse_args()


def sample_with_temperature(probabilities: np.ndarray, temperature: float) -> int:
    probabilities = np.asarray(probabilities).astype("float64")
    probabilities = np.maximum(probabilities, 1e-9)
    logits = np.log(probabilities) / max(temperature, 1e-6)
    exp = np.exp(logits - np.max(logits))
    normalized = exp / np.sum(exp)
    return int(np.random.choice(len(normalized), p=normalized))


def generate_tokens(
    model: keras.Model,
    token_stream: list[str],
    token_to_int: dict[str, int],
    sequence_length: int,
    count: int,
    temperature: float,
    seed_index: int | None,
) -> list[str]:
    int_to_token = {idx: token for token, idx in token_to_int.items()}
    encoded = [token_to_int[token] for token in token_stream]

    max_seed = len(encoded) - sequence_length - 1
    if max_seed < 0:
        raise ValueError("The saved token stream is too short for the sequence length.")

    start = seed_index if seed_index is not None else random.randint(0, max_seed)
    start = max(0, min(start, max_seed))
    pattern = encoded[start : start + sequence_length]

    result: list[str] = []
    for _ in range(count):
        network_input = np.asarray(pattern, dtype=np.int32).reshape(1, sequence_length)
        prediction = model.predict(network_input, verbose=0)[0]
        next_id = sample_with_temperature(prediction, temperature)
        next_token = int_to_token[next_id]
        result.append(next_token)
        pattern = pattern[1:] + [next_id]
    return result


def token_to_music21(token_value: str) -> note.Note | note.Rest | chord.Chord | None:
    if token_value == EOS_TOKEN:
        return None

    kind, value, duration = token_value.split(":")
    quarter_length = max(float(duration), 0.25)

    if kind == "N":
        element = note.Note(value)
    elif kind == "C":
        pitches = [pitch for pitch in value.split(".") if pitch]
        element = chord.Chord(pitches)
    elif kind == "R":
        element = note.Rest()
    else:
        return None

    element.quarterLength = quarter_length
    return element


def write_midi(tokens: list[str], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    piece = stream.Stream()
    piece.append(tempo.MetronomeMark(number=100))

    offset = 0.0
    for token_value in tokens:
        element = token_to_music21(token_value)
        if element is None:
            continue
        piece.insert(offset, element)
        offset += float(element.quarterLength)

    piece.write("midi", fp=str(output_path))


def main() -> None:
    args = parse_args()
    artifacts_dir = Path(args.artifacts_dir)
    metadata = load_json(artifacts_dir / "metadata.json")
    token_stream = load_json(artifacts_dir / "token_stream.json")

    token_to_int = metadata["token_to_int"]
    sequence_length = int(metadata["sequence_length"])
    model = keras.models.load_model(artifacts_dir / "music_lstm.keras")

    generated = generate_tokens(
        model=model,
        token_stream=token_stream,
        token_to_int=token_to_int,
        sequence_length=sequence_length,
        count=args.notes,
        temperature=args.temperature,
        seed_index=args.seed_index,
    )
    write_midi(generated, args.output)
    print(f"Saved generated MIDI to {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
