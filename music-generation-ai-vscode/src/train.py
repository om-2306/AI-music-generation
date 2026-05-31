from __future__ import annotations

import argparse
from pathlib import Path

from tensorflow import keras

from dataset import load_token_stream, prepare_sequences, save_json
from model import build_lstm_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train an LSTM MIDI generator.")
    parser.add_argument("--data-dir", default="data/raw", help="Folder containing MIDI files.")
    parser.add_argument("--artifacts-dir", default="artifacts", help="Where to save outputs.")
    parser.add_argument("--sequence-length", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--embedding-dim", type=int, default=128)
    parser.add_argument("--lstm-units", type=int, default=256)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    artifacts_dir = Path(args.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    tokens = load_token_stream(args.data_dir)
    x, y, token_to_int, _ = prepare_sequences(tokens, args.sequence_length)

    model = build_lstm_model(
        vocab_size=len(token_to_int),
        sequence_length=args.sequence_length,
        embedding_dim=args.embedding_dim,
        lstm_units=args.lstm_units,
    )
    model.summary()

    callbacks = [
        keras.callbacks.ModelCheckpoint(
            filepath=str(artifacts_dir / "music_lstm.keras"),
            monitor="loss",
            save_best_only=True,
        ),
        keras.callbacks.EarlyStopping(
            monitor="loss",
            patience=8,
            restore_best_weights=True,
        ),
    ]

    model.fit(
        x,
        y,
        epochs=args.epochs,
        batch_size=args.batch_size,
        callbacks=callbacks,
        shuffle=True,
    )

    model.save(artifacts_dir / "music_lstm.keras")
    save_json(artifacts_dir / "token_stream.json", tokens)
    save_json(
        artifacts_dir / "metadata.json",
        {
            "sequence_length": args.sequence_length,
            "vocab_size": len(token_to_int),
            "token_to_int": token_to_int,
        },
    )

    print(f"Saved trained model and metadata to {artifacts_dir.resolve()}")


if __name__ == "__main__":
    main()
