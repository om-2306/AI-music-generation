from __future__ import annotations

import importlib.util
import platform
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def status(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def main() -> int:
    print("AI MIDI Studio setup check")
    print("=" * 32)
    print(f"Project folder: {PROJECT_ROOT}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Python executable: {sys.executable}")
    print(f"Operating system: {platform.platform()}")
    print()

    music21_ready = status("music21")
    tensorflow_ready = status("tensorflow")
    print(f"music21 installed: {'YES' if music21_ready else 'NO'}")
    print(f"tensorflow installed: {'YES' if tensorflow_ready else 'NO'}")
    print()

    raw_files = sorted((PROJECT_ROOT / "data" / "raw").glob("*.mid"))
    print(f"MIDI files in data/raw: {len(raw_files)}")
    for file_path in raw_files[:12]:
        print(f"  - {file_path.name}")
    print()

    if sys.version_info >= (3, 13):
        print("Problem found:")
        print("  Your Python version is very new. TensorFlow usually does not support")
        print("  the newest Python versions immediately.")
        print()
        print("Fix:")
        print("  Install Python 3.11 or 3.12, then recreate the .venv using that Python.")
        print()
        print("Example after installing Python 3.11:")
        print("  py -3.11 -m venv .venv")
        print("  .\\.venv\\Scripts\\activate")
        print("  pip install -r requirements.txt")
        print("  python src\\web_app.py")
        return 1

    if not music21_ready or not tensorflow_ready:
        print("Problem found:")
        print("  Required packages are missing.")
        print()
        print("Fix:")
        print("  .\\.venv\\Scripts\\activate")
        print("  pip install -r requirements.txt")
        print("  python src\\web_app.py")
        return 1

    if not raw_files:
        print("Problem found:")
        print("  No MIDI files are present in data/raw.")
        print()
        print("Fix:")
        print("  python src\\make_sample_midi_files.py --output data\\raw")
        return 1

    print("Setup looks ready.")
    print("Run the UI with:")
    print("  python src\\web_app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
