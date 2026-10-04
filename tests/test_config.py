"""Tests for ibroadcast_sync_menubar.config - pure JSON read/write
logic, no AppKit involved."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ibroadcast_sync_menubar import config


@pytest.fixture
def config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirects CONFIG_FILE (and its parent dir) to a throwaway path
    for the duration of a test."""
    path = tmp_path / "config.json"
    monkeypatch.setattr(config, "APP_SUPPORT_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_FILE", path)
    return path


class TestLoadSettings:
    def test_missing_file_returns_defaults(self, config_file: Path) -> None:
        assert config.load_settings() == config.DEFAULT_SETTINGS

    def test_corrupted_file_returns_defaults(self, config_file: Path) -> None:
        config_file.write_text("{not valid json")
        assert config.load_settings() == config.DEFAULT_SETTINGS

    def test_saved_values_round_trip(self, config_file: Path) -> None:
        config.save_settings({**config.DEFAULT_SETTINGS, "client_id": "abc123", "workers": 8})

        loaded = config.load_settings()

        assert loaded["client_id"] == "abc123"
        assert loaded["workers"] == 8

    def test_missing_keys_in_an_old_config_file_fall_back_to_defaults(self, config_file: Path) -> None:
        # Simulates a config.json saved by an older version of the app,
        # missing a key added later.
        config_file.write_text(json.dumps({"client_id": "abc123"}))

        loaded = config.load_settings()

        assert loaded["client_id"] == "abc123"
        assert loaded["do_upload"] == config.DEFAULT_SETTINGS["do_upload"]
        assert loaded["workers"] == config.DEFAULT_SETTINGS["workers"]


class TestSaveSettings:
    def test_save_is_atomic_no_tmp_file_left_behind(self, config_file: Path) -> None:
        config.save_settings(config.DEFAULT_SETTINGS)

        tmp_path = config_file.with_name(config_file.name + ".tmp")
        assert config_file.exists()
        assert not tmp_path.exists()

    def test_save_creates_the_app_support_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app_support_dir = tmp_path / "does" / "not" / "exist" / "yet"
        monkeypatch.setattr(config, "APP_SUPPORT_DIR", app_support_dir)
        monkeypatch.setattr(config, "CONFIG_FILE", app_support_dir / "config.json")

        config.save_settings(config.DEFAULT_SETTINGS)

        assert (app_support_dir / "config.json").exists()
