"""Tests for ibroadcast_sync_menubar.status - pure JSON parsing and
display-string formatting, no AppKit/rumps involved."""

from __future__ import annotations

import json
from pathlib import Path

from ibroadcast_sync_menubar.status import format_status_line, read_status, status_file_path


class TestStatusFilePath:
    def test_defaults_to_project_dir_data_folder(self) -> None:
        assert status_file_path("/Users/me/ibroadcast-sync", "") == Path(
            "/Users/me/ibroadcast-sync/data/ibroadcast_sync_status.json"
        )

    def test_explicit_data_dir_override_wins(self) -> None:
        assert status_file_path("/Users/me/ibroadcast-sync", "/custom/data") == Path(
            "/custom/data/ibroadcast_sync_status.json"
        )


class TestReadStatus:
    def test_nothing_configured_returns_none(self) -> None:
        assert read_status("", "") is None

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert read_status(str(tmp_path), "") is None

    def test_reads_a_real_status_file(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "ibroadcast_sync_status.json").write_text(json.dumps({"success": True, "uploaded": 5}))

        status = read_status(str(tmp_path), "")

        assert status is not None
        assert status["uploaded"] == 5

    def test_corrupted_file_returns_none(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "ibroadcast_sync_status.json").write_text("{not valid json")

        assert read_status(str(tmp_path), "") is None


class TestFormatStatusLine:
    def test_never_synced(self) -> None:
        assert "jamais" in format_status_line(None)

    def test_successful_sync_mentions_counts(self) -> None:
        line = format_status_line(
            {
                "timestamp": "2026-10-03T12:00:00+00:00",
                "success": True,
                "uploaded": 3,
                "playlists_created_or_updated": 2,
            }
        )
        assert "3 envoyé" in line
        assert "2 playlist" in line

    def test_successful_sync_with_nothing_new_says_so(self) -> None:
        line = format_status_line({"timestamp": "2026-10-03T12:00:00+00:00", "success": True})
        assert "rien de nouveau" in line

    def test_failed_sync_mentions_the_error(self) -> None:
        line = format_status_line(
            {"timestamp": "2026-10-03T12:00:00+00:00", "success": False, "error": "boom"}
        )
        assert "échec" in line
        assert "boom" in line

    def test_malformed_timestamp_is_shown_verbatim_rather_than_crashing(self) -> None:
        line = format_status_line({"timestamp": "not-a-date", "success": True})
        assert "not-a-date" in line
