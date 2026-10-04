"""py2app build script - produces a standalone .app bundle (Python
runtime + this package + its dependencies all bundled in), so you can
keep it in ~/Applications and launch it like any other macOS app,
independent of whatever Python install built it.

Usage:
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python3 setup.py py2app -A   # alias/dev build: fast, symlinks back
                                  # to this source tree - use this while
                                  # developing (changes to .py files are
                                  # picked up without rebuilding)
    python3 setup.py py2app      # release build, in dist/ - this is
                                  # the one to actually copy to
                                  # ~/Applications
"""

from setuptools import setup

APP = ["ibroadcast_sync_menubar/app.py"]
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "iBroadcast Sync",
        "CFBundleDisplayName": "iBroadcast Sync",
        "CFBundleIdentifier": "com.jeromearsene.ibroadcast-sync-menubar",
        "CFBundleShortVersionString": "0.1.0",
        # Menu-bar-only app: no Dock icon, no app menu bar at the top of
        # the screen - exactly what rumps.App is designed for.
        "LSUIElement": True,
    },
    "packages": ["rumps"],
}

setup(
    app=APP,
    name="iBroadcast Sync",
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
