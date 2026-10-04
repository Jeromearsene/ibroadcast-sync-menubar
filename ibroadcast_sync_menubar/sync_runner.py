"""Runs a real sync as a subprocess - manual ("Sync now", from app.py)
or, indirectly, scheduled (launchd_manager.py builds the same command
line for the launchd job). Never imports the CLI's own package: the
whole point of this app staying a lightweight menu-bar process is that
requests/rich/oauth_client/etc. only ever run in a short-lived
subprocess, never inside this long-lived one.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence

from .config import Settings


def build_args(settings: Settings) -> list[str]:
    """CLI flags matching the toggles in Settings. Kept separate from
    build_env() so both sync_runner.py (manual run) and
    launchd_manager.py (scheduled run) build the exact same invocation
    from the exact same settings - a manual "Sync now" and tonight's
    scheduled run never silently disagree."""
    args: list[str] = []
    if not settings.get("do_upload", True):
        args.append("--no-upload")
    if not settings.get("do_playlists", True):
        args.append("--no-playlists")
    if settings.get("do_ratings", False):
        args.append("--sync-ratings")
    if settings.get("dry_run", False):
        args.append("--dry-run")
    # Only made explicit when it differs from the CLI's own default (4):
    # matches the rest of this function (every flag here is absent at
    # default settings), and keeps the actual invocation minimal and
    # easy to read in the launchd plist / process list.
    workers = settings.get("workers", 4)
    if workers != 4:
        args.extend(["--workers", str(workers)])
    return args


def build_env(settings: Settings) -> dict[str, str]:
    """Only ever ADDS to a copy of the current environment (never
    starts from an empty one): a launchd job in particular runs with a
    very minimal environment, and the subprocess still needs a normal
    PATH to find `poetry`."""
    env = dict(os.environ)
    client_id = settings.get("client_id", "")
    if client_id:
        env["IBROADCAST_CLIENT_ID"] = client_id
    data_dir = settings.get("data_dir", "")
    if data_dir:
        env["IBROADCAST_DATA_DIR"] = data_dir
    return env


def run_sync_command(settings: Settings) -> Sequence[str]:
    """The exact command line used for both a manual run and the
    scheduled launchd job - calls scripts/run.sh in the ibroadcast-sync
    project itself (the same entry point the project's own README/docs
    point people at for cron/launchd), rather than re-implementing the
    `cd` + `poetry run` dance here."""
    project_dir = settings.get("project_dir", "")
    script = os.path.join(project_dir, "scripts", "run.sh")
    return [script, *build_args(settings)]


def start_sync(settings: Settings) -> subprocess.Popen[bytes]:
    """Starts the sync in the background and returns immediately. The
    caller (app.py, from a worker thread so the menu bar UI never
    blocks) is responsible for waiting on it if it wants to know when
    it's done; it does NOT need the exit code - status.read_status()
    (the status.json the CLI itself writes) is the real source of truth
    for how the run went, including for a scheduled run nobody is
    watching."""
    project_dir = settings.get("project_dir", "")
    return subprocess.Popen(
        run_sync_command(settings),
        cwd=project_dir or None,
        env=build_env(settings),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
