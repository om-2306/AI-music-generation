# Start Here

Open this whole folder in VS Code:

```text
C:\Users\ompra\Documents\Codex\2026-05-31\new-chat\outputs\music-generation-ai
```

Fastest option on Windows:

1. Double-click `OPEN_IN_VSCODE.bat`.
2. In VS Code, open the terminal.
3. Run `setup_windows.bat` once.
4. Run `run_ui.bat`.
5. Open `http://127.0.0.1:8765` in your browser.

If execution does not finish, run this in the VS Code terminal:

```powershell
python check_setup.py
```

It will tell you whether Python, TensorFlow, music21, or the MIDI files are the issue.

What each folder does:

```text
data/raw/      Put training MIDI files here
src/           Python AI, preprocessing, training, generation, and UI server code
ui/            Web UI files
artifacts/     Saved model and metadata after training
generated/     Final AI-generated MIDI files
```

I included sample MIDI files in `data/raw/` so you can test the project immediately.

If TensorFlow installation fails, use Python 3.10, 3.11, or 3.12 for the virtual environment because AI libraries may not support every newest Python version immediately.
