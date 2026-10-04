"""Tests for ibroadcast_sync_menubar.sync_runner's pure command/env
building. start_sync() itself (which actually spawns a process) isn't
exercised here - same reasoning as the rest of this test suite: no
subprocess/AppKit/rumps side effects in the test run."""

from __future__ import annotations

from typing import Any

import pytest

from ibroadcast_sync_menubar.config import DEFAULT_SETTINGS, Settings
from ibroadcast_sync_menubar.sync_runner import build_args, build_env, run_sync_command


def _settings(**overrides: Any) -> Settings:
    return {**DEFAULT_SETTINGS, **overrides}  # type: ignore[typeddict-item]


class TestBuildArgs:
    def test_defaults_produce_no_flags(self) -> None:
        assert build_args(DEFAULT_SETTINGS) == []

    def test_no_upload_flag(self) -> None:
        assert "--no-upload" in build_args(_settings(do_upload=False))

    def test_no_playlists_flag(self) -> None:
        assert "--no-playlists" in build_args(_settings(do_playlists=False))

    def test_sync_ratings_flag(self) -> None:
        assert "--sync-ratings" in build_args(_settings(do_ratings=True))

    def test_dry_run_flag(self) -> None:
        assert "--dry-run" in build_args(_settings(dry_run=True))

    def test_workers_flag(self) -> None:
        args = build_args(_settings(workers=8))
        assert "--workers" in args
        assert "8" in args


class TestBuildEnv:
    def test_preserves_the_existing_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOME_UNRELATED_VAR", "kept")
        env = build_env(DEFAULT_SETTINGS)
        assert env["SOME_UNRELATED_VAR"] == "kept"

    def test_sets_client_id_when_configured(self) -> None:
        env = build_env(_settings(client_id="abc123"))
        assert env["IBROADCAST_CLIENT_ID"] == "abc123"

    def test_omits_client_id_when_not_configured(self) -> None:
        assert "IBROADCAST_CLIENT_ID" not in build_env(DEFAULT_SETTINGS)

    def test_sets_data_dir_override_when_configured(self) -> None:
        env = build_env(_settings(data_dir="/custom/data"))
        assert env["IBROADCAST_DATA_DIR"] == "/custom/data"

    def test_omits_data_dir_when_not_configured(self) -> None:
        assert "IBROADCAST_DATA_DIR" not in build_env(DEFAULT_SETTINGS)


class TestRunSyncCommand:
    def test_calls_the_run_script_in_the_project_dir(self) -> None:
        command = run_sync_command(_settings(project_dir="/Users/me/ibroadcast-sync", dry_run=True))
        assert command[0] == "/Users/me/ibroadcast-sync/scripts/run.sh"
        assert "--dry-run" in command
