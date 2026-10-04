"""Lets the app be started with `python -m ibroadcast_sync_menubar`
during development, without needing the packaged .app bundle."""

from .app import main

if __name__ == "__main__":
    main()
