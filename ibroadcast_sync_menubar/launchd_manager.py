"""Templates and (un)installs the launchd job that runs the sync on a
schedule - the GUI equivalent of manually copying
``docs/com.example.ibroadcast-sync.plist.example`` in the main project
and running launchctl by hand.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

from .config import Settings
from .sync_runner import build_args, build_env

LABEL = "com.jeromearsene.ibroadcast-sync-menubar"
LAUNCH_AGENTS_DIR = Path(os.path.expanduser("~/Library/LaunchAgents"))
PLIST_PATH = LAUNCH_AGENTS_DIR / f"{LABEL}.plist"

# The only environment variables worth persisting into the plist - see
# build_plist()'s docstring for why the rest of build_env()'s output
# (a full os.environ snapshot) is deliberately left out.
_PERSISTED_ENV_VARS = ("IBROADCAST_CLIENT_ID", "IBROADCAST_DATA_DIR")


def build_plist(settings: Settings) -> str:
    """Returns the plist XML as text. Pure string templating (same
    handful of keys as the project's own
    docs/com.example.ibroadcast-sync.plist.example) - deliberately kept
    testable without touching the filesystem or launchctl."""
    project_dir = settings.get("project_dir", "")
    script = os.path.join(project_dir, "scripts", "run.sh")
    args = build_args(settings)
    env = build_env(settings)

    # Only the variables this app actually manages are worth persisting
    # here - re-exporting the whole (huge, machine-specific) os.environ
    # snapshot from build_env() would be both wrong (stale by the time
    # the job runs next, maybe hours or days later) and unreadable if
    # you ever open the plist by hand.
    relevant_env = {k: env[k] for k in _PERSISTED_ENV_VARS if env.get(k)}

    program_arguments = "\n".join(f"    <string>{escape(a)}</string>" for a in (script, *args))
    env_entries = "\n".join(
        f"    <key>{escape(k)}</key>\n    <string>{escape(v)}</string>" for k, v in relevant_env.items()
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{escape(LABEL)}</string>

  <key>EnvironmentVariables</key>
  <dict>
{env_entries}
  </dict>

  <key>ProgramArguments</key>
  <array>
{program_arguments}
  </array>

  <key>WorkingDirectory</key>
  <string>{escape(project_dir)}</string>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>{int(settings.get("schedule_hour", 3))}</integer>
    <key>Minute</key>
    <integer>{int(settings.get("schedule_minute", 0))}</integer>
  </dict>

  <key>StandardOutPath</key>
  <string>/tmp/ibroadcast-sync-menubar.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/ibroadcast-sync-menubar.err</string>
</dict>
</plist>
"""


def install_schedule(settings: Settings) -> None:
    """Writes the plist and (re)loads it - unloading first if a
    previous version is already loaded, since `launchctl load` on an
    already-loaded label is a silent no-op that would leave stale
    settings (old schedule time, old flags) active until the next
    reboot."""
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    if PLIST_PATH.exists():
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)
    PLIST_PATH.write_text(build_plist(settings))
    subprocess.run(["launchctl", "load", "-w", str(PLIST_PATH)], check=True, capture_output=True)


def uninstall_schedule() -> None:
    """Safe to call even if nothing is installed yet - mirrors
    config.load_settings()'s own tolerance for "there's nothing there
    yet"."""
    if not PLIST_PATH.exists():
        return
    subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)
    PLIST_PATH.unlink()


def is_installed() -> bool:
    return PLIST_PATH.exists()
