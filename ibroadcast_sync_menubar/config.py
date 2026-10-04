"""App settings: stored independently of the ibroadcast-sync CLI's own
``.env``, at the standard macOS per-user Application Support location -
so this app's configuration survives even if the CLI's project folder is
moved, reinstalled, or not checked out yet.

Deliberately NOT read by the CLI itself. This app passes what it needs
to the CLI explicitly - as environment variables and flags - each time
it invokes it (see sync_runner.py / launchd_manager.py), rather than
writing into the CLI's own ``.env``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, TypedDict, cast

APP_SUPPORT_DIR = Path(os.path.expanduser("~/Library/Application Support/ibroadcast-sync-menubar"))
CONFIG_FILE = APP_SUPPORT_DIR / "config.json"


class Settings(TypedDict, total=False):
    client_id: str
    project_dir: str  # path to the ibroadcast-sync checkout (where scripts/run.sh lives)
    data_dir: str  # optional override of IBROADCAST_DATA_DIR ("" = project's own data/ folder)
    do_upload: bool
    do_playlists: bool
    do_ratings: bool
    dry_run: bool
    workers: int
    schedule_enabled: bool
    schedule_hour: int
    schedule_minute: int


# Also serves as the canonical list of known keys: load_settings() merges
# saved data over this, so a config file from an older version of the
# app (missing a key added later) still loads with a sane value for it.
DEFAULT_SETTINGS: Settings = {
    "client_id": "",
    "project_dir": "",
    "data_dir": "",
    "do_upload": True,
    "do_playlists": True,
    "do_ratings": False,
    "dry_run": False,
    "workers": 4,
    "schedule_enabled": False,
    "schedule_hour": 3,
    "schedule_minute": 0,
}


def load_settings() -> Settings:
    """Returns saved settings merged over the defaults. Never raises: a
    missing or corrupted config file (first run, a bad manual edit)
    just falls back to defaults, the same tolerance ibroadcast-sync's
    own md5_cache.load_state() has for its cache file."""
    try:
        with open(CONFIG_FILE) as f:
            data: Any = json.load(f)
    except Exception:
        data = {}
    merged: dict[str, Any] = {**DEFAULT_SETTINGS, **(data if isinstance(data, dict) else {})}
    return cast("Settings", merged)


def save_settings(settings: Settings) -> None:
    """Atomic write (temp file + os.replace), same pattern as
    ibroadcast_sync.md5_cache/status in the main project: a reader never
    observes a half-written, corrupted config file."""
    APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = CONFIG_FILE.with_name(CONFIG_FILE.name + ".tmp")
    with open(tmp_path, "w") as f:
        json.dump(settings, f, indent=2)
    os.replace(tmp_path, CONFIG_FILE)
