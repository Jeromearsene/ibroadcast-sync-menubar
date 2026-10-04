"""Menu bar companion app for ibroadcast-sync.

Deliberately minimal: this long-lived process only ever imports
rumps/PyObjC plus the stdlib (json, pathlib, subprocess, threading). The
actual sync - and everything that comes with it (requests, rich,
oauth_client, the Music.app JXA bridge, ...) - always runs in a
separate, short-lived subprocess (see sync_runner.py), whether
triggered manually ("Synchroniser maintenant") or on a launchd schedule
(launchd_manager.py). That split is what keeps this app's own memory/CPU
footprint tiny and *constant* - whether or not a sync is currently
running, and regardless of library size.

Threading note: the background thread started by on_sync_now() below
touches NOTHING AppKit/rumps-related - it only flips a plain `bool`
(``self._sync_in_progress``), which the main-thread timers below pick
up and act on. Updating menu items/icons is only ever done from a
rumps.Timer callback or a menu click handler, both of which run on the
main thread (NSTimer/NSMenu-backed) - never from the worker thread
itself. This is what keeps the UI responsive and avoids the undefined
behaviour of touching AppKit objects off the main thread.
"""

from __future__ import annotations

import threading

import rumps

from . import launchd_manager
from .config import Settings, load_settings, save_settings
from .settings_window import choose_project_folder
from .status import format_status_line, read_status
from .sync_runner import start_sync

REFRESH_INTERVAL_SECONDS = 30
POLL_INTERVAL_WHILE_SYNCING_SECONDS = 2


class IBroadcastSyncApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("iBroadcast Sync", title="⏺", quit_button="Quitter")
        self.settings: Settings = load_settings()
        self._sync_in_progress = False
        self._poll_timer: rumps.Timer | None = None

        self.status_item = rumps.MenuItem("Dernière synchro : jamais")
        self.sync_item = rumps.MenuItem("Synchroniser maintenant", callback=self.on_sync_now)

        self.upload_item = rumps.MenuItem("Upload", callback=self.on_toggle_upload)
        self.playlists_item = rumps.MenuItem("Playlists", callback=self.on_toggle_playlists)
        self.ratings_item = rumps.MenuItem("Notes (ratings)", callback=self.on_toggle_ratings)
        self.dry_run_item = rumps.MenuItem("Mode simulation (dry-run)", callback=self.on_toggle_dry_run)

        self.project_dir_item = rumps.MenuItem("Dossier du projet…", callback=self.on_choose_project_dir)
        self.client_id_item = rumps.MenuItem("Client ID…", callback=self.on_edit_client_id)
        self.workers_item = rumps.MenuItem("Parallélisme…", callback=self.on_edit_workers)

        self.schedule_enabled_item = rumps.MenuItem(
            "Synchro planifiée activée", callback=self.on_toggle_schedule
        )
        self.schedule_time_item = rumps.MenuItem("Heure de la synchro…", callback=self.on_edit_schedule_time)

        self._sync_toggle_states_from_settings()

        self.menu = [
            self.status_item,
            None,
            self.sync_item,
            None,
            self.upload_item,
            self.playlists_item,
            self.ratings_item,
            self.dry_run_item,
            None,
            self.project_dir_item,
            self.client_id_item,
            self.workers_item,
            None,
            self.schedule_enabled_item,
            self.schedule_time_item,
        ]

        self.refresh_status()
        self.timer = rumps.Timer(self.on_timer, REFRESH_INTERVAL_SECONDS)
        self.timer.start()

    # -- Keeping menu state in sync with settings --------------------------

    def _sync_toggle_states_from_settings(self) -> None:
        self.upload_item.state = bool(self.settings.get("do_upload", True))
        self.playlists_item.state = bool(self.settings.get("do_playlists", True))
        self.ratings_item.state = bool(self.settings.get("do_ratings", False))
        self.dry_run_item.state = bool(self.settings.get("dry_run", False))
        self.schedule_enabled_item.state = bool(self.settings.get("schedule_enabled", False))

    def _save(self) -> None:
        save_settings(self.settings)

    # -- Status display -----------------------------------------------------

    def refresh_status(self) -> None:
        status = read_status(self.settings.get("project_dir", ""), self.settings.get("data_dir", ""))
        self.status_item.title = format_status_line(status)
        if self._sync_in_progress:
            self.title = "🔄"
        elif status is not None and not status.get("success", True):
            self.title = "⚠️"
        else:
            self.title = "⏺"

    def on_timer(self, _sender: rumps.Timer) -> None:
        # The dedicated, faster _poll_timer (started in on_sync_now)
        # handles refreshing while a sync is running - this one just
        # stays out of its way.
        if not self._sync_in_progress:
            self.refresh_status()

    # -- Sync now -------------------------------------------------------------

    def on_sync_now(self, _sender: rumps.MenuItem) -> None:
        if self._sync_in_progress:
            return
        if not self.settings.get("project_dir"):
            rumps.alert(
                "Dossier du projet manquant",
                "Choisis d'abord le dossier du projet ibroadcast-sync (menu « Dossier du projet… »).",
            )
            return
        self._sync_in_progress = True
        self.sync_item.title = "Synchronisation en cours…"
        self.title = "🔄"
        threading.Thread(target=self._run_sync_in_background, daemon=True).start()
        if self._poll_timer is None:
            self._poll_timer = rumps.Timer(self._poll_sync_progress, POLL_INTERVAL_WHILE_SYNCING_SECONDS)
        self._poll_timer.start()

    def _run_sync_in_background(self) -> None:
        """Runs on a worker thread - see the module docstring for why
        this only ever flips a plain bool, never touches rumps/AppKit
        directly."""
        try:
            process = start_sync(self.settings)
            process.wait()
        finally:
            self._sync_in_progress = False

    def _poll_sync_progress(self, sender: rumps.Timer) -> None:
        """Runs on the main thread (rumps.Timer is NSTimer-backed) -
        safe to touch menu items/icons here."""
        if self._sync_in_progress:
            return
        sender.stop()
        self.sync_item.title = "Synchroniser maintenant"
        self.refresh_status()

    # -- Toggles ----------------------------------------------------------

    def on_toggle_upload(self, sender: rumps.MenuItem) -> None:
        sender.state = not sender.state
        self.settings["do_upload"] = bool(sender.state)
        self._save()

    def on_toggle_playlists(self, sender: rumps.MenuItem) -> None:
        sender.state = not sender.state
        self.settings["do_playlists"] = bool(sender.state)
        self._save()

    def on_toggle_ratings(self, sender: rumps.MenuItem) -> None:
        sender.state = not sender.state
        self.settings["do_ratings"] = bool(sender.state)
        self._save()

    def on_toggle_dry_run(self, sender: rumps.MenuItem) -> None:
        sender.state = not sender.state
        self.settings["dry_run"] = bool(sender.state)
        self._save()

    # -- Simple value prompts ------------------------------------------------

    def on_choose_project_dir(self, _sender: rumps.MenuItem) -> None:
        chosen = choose_project_folder(self.settings.get("project_dir", ""))
        if chosen:
            self.settings["project_dir"] = chosen
            self._save()
            self.refresh_status()

    def on_edit_client_id(self, _sender: rumps.MenuItem) -> None:
        response = rumps.Window(
            title="Client ID iBroadcast",
            message="Identifiant de ton app créée sur ibroadcast.com (section Developer).",
            default_text=self.settings.get("client_id", ""),
            ok="Enregistrer",
            cancel="Annuler",
        ).run()
        if response.clicked:
            self.settings["client_id"] = response.text.strip()
            self._save()

    def on_edit_workers(self, _sender: rumps.MenuItem) -> None:
        response = rumps.Window(
            title="Parallélisme",
            message="Nombre de fichiers traités (hash + upload) en parallèle.",
            default_text=str(self.settings.get("workers", 4)),
            ok="Enregistrer",
            cancel="Annuler",
        ).run()
        if not response.clicked:
            return
        try:
            self.settings["workers"] = max(1, int(response.text.strip()))
            self._save()
        except ValueError:
            rumps.alert("Valeur invalide", "Indique un nombre entier positif.")

    # -- Scheduling ---------------------------------------------------------

    def on_toggle_schedule(self, sender: rumps.MenuItem) -> None:
        sender.state = not sender.state
        self.settings["schedule_enabled"] = bool(sender.state)
        self._save()
        try:
            if sender.state:
                launchd_manager.install_schedule(self.settings)
            else:
                launchd_manager.uninstall_schedule()
        except Exception as e:
            rumps.alert("Erreur de planification", str(e))

    def on_edit_schedule_time(self, _sender: rumps.MenuItem) -> None:
        hour = int(self.settings.get("schedule_hour", 3))
        minute = int(self.settings.get("schedule_minute", 0))
        response = rumps.Window(
            title="Heure de la synchro planifiée",
            message="Format HH:MM (heure locale).",
            default_text=f"{hour:02d}:{minute:02d}",
            ok="Enregistrer",
            cancel="Annuler",
        ).run()
        if not response.clicked:
            return
        try:
            hour_str, minute_str = response.text.strip().split(":")
            new_hour, new_minute = int(hour_str), int(minute_str)
            if not (0 <= new_hour <= 23 and 0 <= new_minute <= 59):
                raise ValueError
        except ValueError:
            rumps.alert("Format invalide", "Utilise le format HH:MM, par exemple 03:00.")
            return
        self.settings["schedule_hour"] = new_hour
        self.settings["schedule_minute"] = new_minute
        self._save()
        if self.settings.get("schedule_enabled"):
            try:
                launchd_manager.install_schedule(self.settings)
            except Exception as e:
                rumps.alert("Erreur de planification", str(e))


def main() -> None:
    IBroadcastSyncApp().run()


if __name__ == "__main__":
    main()
