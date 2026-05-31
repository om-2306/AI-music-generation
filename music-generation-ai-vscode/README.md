# AI Music Generation with MIDI

This project implements the full task pipeline:

1. Collect MIDI files in `data/raw`.
2. Preprocess MIDI notes, chords, and rests with `music21`.
3. Train an LSTM model to learn token sequences.
4. Generate a new token sequence from the trained model.
5. Convert the generated sequence back into a playable `.mid` file.

## Project Structure

```text
music-generation-ai/
  data/raw/              # Put .mid or .midi training files here
  artifacts/             # Trained model and metadata are saved here
  generated/             # Generated MIDI files are saved here
  ui/                    # Web interface
  src/
    dataset.py           # MIDI parsing and sequence preparation
    model.py             # LSTM model definition
    train.py             # Training entry point
    generate.py          # Music generation entry point
    make_demo_midi.py    # Optional tiny demo dataset generator
```

## Open in VS Code

Open this folder in VS Code:

```text
C:\Users\ompra\Documents\Codex\2026-05-31\new-chat\outputs\music-generation-ai
```

On Windows you can also double-click:

```text
OPEN_IN_VSCODE.bat
```

Then read `START_HERE.md`.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Open the UI

```powershell
python src/web_app.py
```

Then open:

```text
http://127.0.0.1:8765
```

The UI lets you add MIDI files, create demo MIDI files, train the model, generate new MIDI, and watch the command output in the execution panel.

## Add Training Data

Place classical, jazz, or other MIDI files in:

```text
data/raw/
```

This project already includes generated sample MIDI files in `data/raw` for a quick first run.

For a quick smoke test without downloading a dataset, create a tiny demo dataset:

```powershell
python src/make_demo_midi.py --output data/raw --count 12
```

If `music21` is not installed yet, you can create dependency-free sample files instead:

```powershell
python src/make_sample_midi_files.py --output data/raw
```

The demo files are intentionally small. For better results, use a larger dataset with hundreds or thousands of MIDI files.

## Train

```powershell
python src/train.py --data-dir data/raw --epochs 50 --batch-size 64
```

Useful faster test run:

```powershell
python src/train.py --data-dir data/raw --epochs 3 --batch-size 16 --sequence-length 32
```

Training creates:

```text
artifacts/music_lstm.keras
artifacts/metadata.json
artifacts/token_stream.json
```

## Generate MIDI

```powershell
python src/generate.py --notes 200 --output generated/generated_music.mid
```

You can play the generated `.mid` file in any MIDI player or import it into a DAW.

## How It Works

- Notes are encoded as `N:<pitch>:<duration>`, for example `N:C4:1.00`.
- Chords are encoded as `C:<pitches>:<duration>`, for example `C:C3.E3.G3:2.00`.
- Rests are encoded as `R:REST:<duration>`.
- The LSTM learns to predict the next token from the previous `sequence_length` tokens.
- During generation, predictions are sampled with temperature so the output can be more conservative or more surprising.

Lower temperature values such as `0.5` produce safer, more repetitive music. Higher values such as `1.2` produce more variety.
