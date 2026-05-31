from __future__ import annotations

from tensorflow import keras
from tensorflow.keras import layers


def build_lstm_model(
    vocab_size: int,
    sequence_length: int,
    embedding_dim: int = 128,
    lstm_units: int = 256,
) -> keras.Model:
    model = keras.Sequential(
        [
            keras.Input(shape=(sequence_length,), name="token_ids"),
            layers.Embedding(vocab_size, embedding_dim, name="token_embedding"),
            layers.LSTM(lstm_units, return_sequences=True),
            layers.Dropout(0.3),
            layers.LSTM(max(lstm_units // 2, 64)),
            layers.Dense(256, activation="relu"),
            layers.Dropout(0.3),
            layers.Dense(vocab_size, activation="softmax"),
        ]
    )
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model
