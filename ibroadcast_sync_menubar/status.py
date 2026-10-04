"""Reads the CLI's small run-status file
(``<data_dir>/ibroadcast_sync_status.json``, written by
``ibroadcast_sync.status.write_status`` in the main project) and formats
it for display in the menu.

Deliberately duplicated here rather than imported from the CLI project:
the whole point of invoking the sync as a subprocess (see
sync_runner.py) is that this long-lived GUI process never imports the
CLI's heavier dependencies (requests, rich, ...). Reading one small JSON
file directly costs nothing and keeps that boundary real, not just
nominal.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict, cast


class SyncStatus(TypedDict, total=False):
    timestamp: str
    success: bool
    error: str | None
    dry_run: bool
    uploaded: int
    upload_failed: int
    playlists_created_or_updated: int
    playlists_unmatched_tracks: int
    ratings_updated: int
    ratings_failed: int


def status_file_path(project_dir: str, data_dir: str) -> Path:
    """Mirrors ibroadcast_sync.config.DATA_DIR's own resolution in the
    main project: an explicit data_dir override if one is configured,
    otherwise ``<project_dir>/data``."""
    base = Path(data_dir) if data_dir else Path(project_dir) / "data"
    return base / "ibroadcast_sync_status.json"


def read_status(project_dir: str, data_dir: str) -> SyncStatus | None:
    """Returns the last written status, or None if there isn't one yet,
    the project folder isn't configured, or the file can't be read
    (corrupted, concurrent write mid-sync)."""
    if not project_dir and not data_dir:
        return None
    try:
        with open(status_file_path(project_dir, data_dir)) as f:
            data: Any = json.load(f)
    except Exception:
        return None
    return cast("SyncStatus | None", data if isinstance(data, dict) else None)


def _format_timestamp(ts: str) -> str:
    if not ts:
        return "?"
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        # Shown as-is rather than crashing the menu bar over a status
        # file written by some future, incompatible version of the CLI.
        return ts
    return dt.astimezone().strftime("%d/%m %H:%M")


def format_status_line(status: SyncStatus | None) -> str:
    """One-line summary for the menu's top (disabled) item. Pure
    string formatting - no filesystem access - so it's trivially
    testable without touching disk."""
    if status is None:
        return "Dernière synchro : jamais"

    when = _format_timestamp(status.get("timestamp", ""))

    if not status.get("success", True):
        detail = status.get("error") or "erreur inconnue"
        return f"Dernière synchro : échec ({when}) — {detail}"

    parts = []
    if "uploaded" in status:
        parts.append(f"{status['uploaded']} envoyé(s)")
    if "playlists_created_or_updated" in status:
        parts.append(f"{status['playlists_created_or_updated']} playlist(s)")
    if "ratings_updated" in status:
        parts.append(f"{status['ratings_updated']} note(s)")
    detail = ", ".join(parts) if parts else "rien de nouveau"

    return f"Dernière synchro : {when} — {detail}"
