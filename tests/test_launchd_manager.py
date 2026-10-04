"""Tests for ibroadcast_sync_menubar.launchd_manager's plist templating -
pure string building, no filesystem or launchctl calls."""

from __future__ import annotations

from typing import Any

from ibroadcast_sync_menubar.config import DEFAULT_SETTINGS, Settings
from ibroadcast_sync_menubar.launchd_manager import LABEL, build_plist


def _settings(**overrides: Any) -> Settings:
    return {**DEFAULT_SETTINGS, **overrides}  # type: ignore[typeddict-item]


class TestBuildPlist:
    def test_includes_the_label(self) -> None:
        xml = build_plist(_settings(project_dir="/Users/me/ibroadcast-sync"))
        assert f"<string>{LABEL}</string>" in xml

    def test_includes_the_run_script_and_working_directory(self) -> None:
        xml = build_plist(_settings(project_dir="/Users/me/ibroadcast-sync"))
        assert "/Users/me/ibroadcast-sync/scripts/run.sh" in xml
        assert "<string>/Users/me/ibroadcast-sync</string>" in xml

    def test_includes_the_schedule(self) -> None:
        xml = build_plist(_settings(project_dir="/p", schedule_hour=4, schedule_minute=30))
        assert "<integer>4</integer>" in xml
        assert "<integer>30</integer>" in xml

    def test_includes_the_relevant_flags(self) -> None:
        xml = build_plist(_settings(project_dir="/p", do_playlists=False, dry_run=True))
        assert "<string>--no-playlists</string>" in xml
        assert "<string>--dry-run</string>" in xml

    def test_includes_client_id_but_not_the_whole_environment(self) -> None:
        xml = build_plist(_settings(project_dir="/p", client_id="abc123"))
        assert "<string>abc123</string>" in xml
        assert "IBROADCAST_CLIENT_ID" in xml
        # Only the two variables this app manages are persisted - not a
        # snapshot of the whole (machine-specific, stale-by-next-run)
        # os.environ.
        assert "PATH" not in xml

    def test_omits_the_env_vars_dict_entries_when_nothing_is_configured(self) -> None:
        xml = build_plist(_settings(project_dir="/p"))
        assert "IBROADCAST_CLIENT_ID" not in xml
        assert "IBROADCAST_DATA_DIR" not in xml

    def test_escapes_special_characters(self) -> None:
        xml = build_plist(_settings(project_dir="/Users/me/Musique & Cie"))
        assert "&amp;" in xml
