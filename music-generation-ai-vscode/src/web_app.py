from __future__ import annotations

import base64
import importlib.util
import itertools
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_DIR = PROJECT_ROOT / "ui"
DATA_DIR = PROJECT_ROOT / "data" / "raw"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
GENERATED_DIR = PROJECT_ROOT / "generated"
SRC_DIR = PROJECT_ROOT / "src"

JOBS: dict[int, dict[str, object]] = {}
JOB_COUNTER = itertools.count(1)
JOB_LOCK = threading.Lock()


def json_response(handler: BaseHTTPRequestHandler, payload: object, status: int = 200) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json(handler: BaseHTTPRequestHandler) -> dict[str, object]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length == 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def safe_name(filename: str) -> str:
    filename = Path(filename).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
    return cleaned or "uploaded.mid"


def list_files(path: Path, extensions: tuple[str, ...]) -> list[dict[str, object]]:
    path.mkdir(parents=True, exist_ok=True)
    items = []
    for file_path in sorted(path.iterdir()):
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            items.append(
                {
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                }
            )
    return items


def module_status(module_name: str) -> dict[str, object]:
    spec = importlib.util.find_spec(module_name)
    return {"name": module_name, "installed": spec is not None}


def status_payload() -> dict[str, object]:
    metadata = ARTIFACTS_DIR / "metadata.json"
    model = ARTIFACTS_DIR / "music_lstm.keras"
    return {
        "dependencies": [module_status("music21"), module_status("tensorflow")],
        "rawMidiCount": len(list_files(DATA_DIR, (".mid", ".midi"))),
        "generatedCount": len(list_files(GENERATED_DIR, (".mid", ".midi"))),
        "modelReady": metadata.exists() and model.exists(),
        "metadataReady": metadata.exists(),
        "projectRoot": str(PROJECT_ROOT),
    }


def build_command(action: str, params: dict[str, object]) -> tuple[list[str], str]:
    if action == "demo":
        count = int(params.get("count", 12))
        return (
            [
                sys.executable,
                "-u",
                str(SRC_DIR / "make_demo_midi.py"),
                "--output",
                str(DATA_DIR),
                "--count",
                str(max(1, min(count, 100))),
            ],
            "Create demo MIDI dataset",
        )

    if action == "train":
        epochs = int(params.get("epochs", 3))
        batch_size = int(params.get("batchSize", 16))
        sequence_length = int(params.get("sequenceLength", 32))
        return (
            [
                sys.executable,
                "-u",
                str(SRC_DIR / "train.py"),
                "--data-dir",
                str(DATA_DIR),
                "--artifacts-dir",
                str(ARTIFACTS_DIR),
                "--epochs",
                str(max(1, min(epochs, 500))),
                "--batch-size",
                str(max(1, min(batch_size, 512))),
                "--sequence-length",
                str(max(8, min(sequence_length, 256))),
            ],
            "Train LSTM model",
        )

    if action == "generate":
        notes = int(params.get("notes", 200))
        temperature = float(params.get("temperature", 0.8))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = GENERATED_DIR / f"generated_music_{timestamp}.mid"
        return (
            [
                sys.executable,
                "-u",
                str(SRC_DIR / "generate.py"),
                "--artifacts-dir",
                str(ARTIFACTS_DIR),
                "--output",
                str(output),
                "--notes",
                str(max(16, min(notes, 2000))),
                "--temperature",
                str(max(0.1, min(temperature, 2.0))),
            ],
            "Generate MIDI",
        )

    raise ValueError(f"Unknown action: {action}")


def run_job(job_id: int, command: list[str]) -> None:
    with JOB_LOCK:
        job = JOBS[job_id]
        job["status"] = "running"
        job["logs"] = [f"$ {' '.join(command)}"]

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    try:
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        assert process.stdout is not None
        for line in process.stdout:
            with JOB_LOCK:
                JOBS[job_id]["logs"].append(line.rstrip())
        return_code = process.wait()
        with JOB_LOCK:
            JOBS[job_id]["status"] = "completed" if return_code == 0 else "failed"
            JOBS[job_id]["returnCode"] = return_code
            JOBS[job_id]["finishedAt"] = datetime.now().isoformat()
    except Exception as exc:
        with JOB_LOCK:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["logs"].append(str(exc))
            JOBS[job_id]["returnCode"] = -1
            JOBS[job_id]["finishedAt"] = datetime.now().isoformat()


def serve_file(handler: BaseHTTPRequestHandler, path: Path, download_name: str | None = None) -> None:
    if not path.exists() or not path.is_file():
        handler.send_error(HTTPStatus.NOT_FOUND, "File not found")
        return
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = path.read_bytes()
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", mime)
    handler.send_header("Content-Length", str(len(body)))
    if download_name:
        handler.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
    handler.end_headers()
    handler.wfile.write(body)


class MusicUiHandler(BaseHTTPRequestHandler):
    server_version = "MusicGenerationUI/1.0"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path

        if route == "/api/status":
            json_response(self, status_payload())
            return

        if route == "/api/files":
            json_response(
                self,
                {
                    "raw": list_files(DATA_DIR, (".mid", ".midi")),
                    "generated": list_files(GENERATED_DIR, (".mid", ".midi")),
                },
            )
            return

        if route.startswith("/api/jobs/"):
            job_id = int(route.rsplit("/", 1)[-1])
            with JOB_LOCK:
                job = JOBS.get(job_id)
                payload = dict(job) if job else None
            if payload is None:
                json_response(self, {"error": "Job not found"}, HTTPStatus.NOT_FOUND)
            else:
                json_response(self, payload)
            return

        if route.startswith("/generated/"):
            name = safe_name(unquote(route.removeprefix("/generated/")))
            serve_file(self, GENERATED_DIR / name, download_name=name)
            return

        if route == "/":
            serve_file(self, UI_DIR / "index.html")
            return

        requested = (UI_DIR / unquote(route.lstrip("/"))).resolve()
        if UI_DIR.resolve() not in requested.parents and requested != UI_DIR.resolve():
            handler_error = "Forbidden"
            self.send_error(HTTPStatus.FORBIDDEN, handler_error)
            return
        serve_file(self, requested)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path

        if route == "/api/upload":
            payload = read_json(self)
            filename = safe_name(str(payload.get("filename", "uploaded.mid")))
            if Path(filename).suffix.lower() not in {".mid", ".midi"}:
                json_response(self, {"error": "Only .mid and .midi files are accepted."}, 400)
                return
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            encoded = str(payload.get("content", ""))
            file_bytes = base64.b64decode(encoded)
            target = DATA_DIR / filename
            target.write_bytes(file_bytes)
            json_response(self, {"ok": True, "file": filename, "size": len(file_bytes)})
            return

        if route == "/api/jobs":
            payload = read_json(self)
            action = str(payload.get("action", ""))
            params = payload.get("params", {})
            if not isinstance(params, dict):
                params = {}

            with JOB_LOCK:
                running = [
                    job for job in JOBS.values() if job.get("status") in {"queued", "running"}
                ]
            if running:
                json_response(self, {"error": "A job is already running."}, HTTPStatus.CONFLICT)
                return

            try:
                command, label = build_command(action, params)
            except Exception as exc:
                json_response(self, {"error": str(exc)}, 400)
                return

            job_id = next(JOB_COUNTER)
            with JOB_LOCK:
                JOBS[job_id] = {
                    "id": job_id,
                    "action": action,
                    "label": label,
                    "status": "queued",
                    "logs": [],
                    "createdAt": datetime.now().isoformat(),
                    "returnCode": None,
                }

            thread = threading.Thread(target=run_job, args=(job_id, command), daemon=True)
            thread.start()
            json_response(self, JOBS[job_id], HTTPStatus.CREATED)
            return

        json_response(self, {"error": "Route not found"}, HTTPStatus.NOT_FOUND)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), MusicUiHandler)
    print(f"Music generation UI running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
