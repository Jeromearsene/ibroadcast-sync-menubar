"""Thin AppKit helper: a native macOS folder picker (NSOpenPanel) for
choosing the ibroadcast-sync project folder.

Deliberately just this one function, rather than a hand-built AppKit
settings form: every other control in this app's "Réglages" experience
is built from rumps' own simple, well-tested primitives directly in the
menu (checkable menu items for on/off toggles, ``rumps.Window`` for the
one or two free-text values) - see app.py. Fewer moving parts than a
custom NSWindow, and every control is a standard native macOS widget
the person already knows from every other menu bar app.

Not covered by this project's test suite, like the rest of the
AppKit/rumps glue code (see README.md) - there's no macOS/PyObjC runtime
to actually exercise it outside a real Mac. It's still checked with
``python -m py_compile`` and, since AppKit's types are declared
``Any`` for mypy here (see pyproject.toml), with mypy too.
"""

from __future__ import annotations

from AppKit import NSApp, NSOpenPanel
from Foundation import NSURL


def choose_project_folder(start_path: str = "") -> str | None:
    """Opens a native folder-choosing panel and returns the chosen
    path, or None if the user cancelled. Blocks (``runModal``) - this
    is only ever called from a menu click, already on the main thread,
    so that's exactly the synchronous, modal interaction the person
    expects from clicking a "choose folder" menu item."""
    panel = NSOpenPanel.openPanel()
    panel.setCanChooseDirectories_(True)
    panel.setCanChooseFiles_(False)
    panel.setAllowsMultipleSelection_(False)
    panel.setPrompt_("Choisir")
    if start_path:
        panel.setDirectoryURL_(NSURL.fileURLWithPath_(start_path))

    # This app runs with LSUIElement=True (see setup.py) so it has no Dock
    # icon and is never activated by macOS on its own. Without this, the
    # panel opens but never reliably becomes key: clicking a row to
    # navigate into a subfolder gets treated as ending the modal session
    # instead of as a navigation click, so the panel appears to close on
    # the first click into any folder. Activating the app first fixes it.
    NSApp().activateIgnoringOtherApps_(True)

    if panel.runModal():  # NSModalResponseOK
        urls = panel.URLs()
        if urls:
            return str(urls[0].path())
    return None
