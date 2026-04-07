import json
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


SCRIPT_DIR = Path(__file__).resolve().parent
MARKDOWN_DIR = SCRIPT_DIR / "paper_in_markdown"
RESULT_DIR = SCRIPT_DIR / "result"
CHECKPOINT_FILE = RESULT_DIR / "progress_checkpoint.json"
RUNTIME_STATUS_FILE = RESULT_DIR / "runtime_status.json"
JSON_OUTPUT_DIR = RESULT_DIR / "json_outputs"
PROCESS_LOG_FILE = RESULT_DIR / "process_runtime.log"

_process_lock = threading.Lock()
_process_handle: subprocess.Popen | None = None


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _safe_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _format_seconds(seconds: float) -> str:
    sec = max(int(seconds), 0)
    hours, rem = divmod(sec, 3600)
    minutes, s = divmod(rem, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {s}s"
    if minutes > 0:
        return f"{minutes}m {s}s"
    return f"{s}s"


def build_snapshot() -> dict:
    markdown_files = sorted(MARKDOWN_DIR.glob("*.md")) if MARKDOWN_DIR.exists() else []
    total = len(markdown_files)

    checkpoint = _read_json(
        CHECKPOINT_FILE,
        {"completed": [], "failed": [], "completed_files": [], "failed_files": []},
    )
    completed_files = set(checkpoint.get("completed_files", []))
    failed_files = set(checkpoint.get("failed_files", []))

    # Backward compatibility with serial-only checkpoints.
    serial_to_name = {str(i): p.name for i, p in enumerate(markdown_files, start=1)}
    for serial in checkpoint.get("completed", []):
        if serial in serial_to_name:
            completed_files.add(serial_to_name[serial])
    for serial in checkpoint.get("failed", []):
        if serial in serial_to_name:
            failed_files.add(serial_to_name[serial])

    all_names = [p.name for p in markdown_files]
    pending = [name for name in all_names if name not in completed_files]

    recent_json = []
    if JSON_OUTPUT_DIR.exists():
        files = sorted(
            JSON_OUTPUT_DIR.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:8]
        recent_json = [
            {"file": p.name, "modified_at": _safe_iso(p.stat().st_mtime)} for p in files
        ]

    runtime = _read_json(RUNTIME_STATUS_FILE, {"state": "idle", "message": "Not started"})

    completed_count = len([x for x in all_names if x in completed_files])
    failed_count = len([x for x in all_names if x in failed_files])
    percent = (completed_count / total * 100) if total else 0
    pending_count = max(total - completed_count, 0)
    avg_file_seconds = float(runtime.get("avg_file_seconds", 0.0) or 0.0)
    eta_seconds = pending_count * avg_file_seconds if avg_file_seconds > 0 else None

    is_running = False
    pid = None
    with _process_lock:
        if _process_handle and _process_handle.poll() is None:
            is_running = True
            pid = _process_handle.pid

    return {
        "totals": {
            "total": total,
            "completed": completed_count,
            "failed": failed_count,
            "pending": pending_count,
            "progress_percent": round(percent, 2),
        },
        "runtime": {
            **runtime,
            "eta_seconds": round(eta_seconds, 2) if eta_seconds is not None else None,
            "eta_human": _format_seconds(eta_seconds) if eta_seconds is not None else "N/A",
            "avg_file_seconds": round(avg_file_seconds, 2),
            "avg_file_human": _format_seconds(avg_file_seconds)
            if avg_file_seconds > 0
            else "N/A",
        },
        "runner": {"is_running": is_running, "pid": pid},
        "pending_files_preview": pending[:20],
        "recent_outputs": recent_json,
        "checkpoint_file": str(CHECKPOINT_FILE),
        "runtime_file": str(RUNTIME_STATUS_FILE),
    }


app = FastAPI(title="Literature Extractor Mission Control API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/status")
def status():
    return build_snapshot()


@app.post("/api/run/start")
def run_start():
    global _process_handle
    with _process_lock:
        if _process_handle and _process_handle.poll() is None:
            return {
                "ok": False,
                "message": "process_papers.py is already running",
                "pid": _process_handle.pid,
            }

        RESULT_DIR.mkdir(exist_ok=True)
        log_file = open(PROCESS_LOG_FILE, "a", encoding="utf-8")
        try:
            _process_handle = subprocess.Popen(
                [sys.executable, str(SCRIPT_DIR / "process_papers.py")],
                cwd=str(SCRIPT_DIR),
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
        finally:
            log_file.close()
        return {
            "ok": True,
            "message": "Started process_papers.py",
            "pid": _process_handle.pid,
            "log_file": str(PROCESS_LOG_FILE),
        }


@app.post("/api/run/stop")
def run_stop():
    global _process_handle
    with _process_lock:
        if not _process_handle or _process_handle.poll() is not None:
            _process_handle = None
            return {"ok": False, "message": "No active process to stop"}

        proc = _process_handle
        proc.terminate()

    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)

    with _process_lock:
        _process_handle = None

    return {"ok": True, "message": "Stopped process_papers.py"}
