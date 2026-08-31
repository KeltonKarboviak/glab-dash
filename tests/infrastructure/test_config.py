from pathlib import Path

import pytest

from glab_dash.domain.config import ConfigError, MergeRequestState, Scope
from glab_dash.infrastructure.config import load_config, resolve_config_path


def write_config(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


class TestLoadConfig:
    def test_parses_sections_in_yaml_order(self, tmp_path: Path) -> None:
        config_path = write_config(
            tmp_path / "config.yml",
            """
            sections:
              - title: "My Reviews"
                scope: project
                project: "group/project-path"
              - title: "Team MRs"
                scope: group
                group: "group-path"
                state: merged
                author: "@me"
                assignee: "someone"
                labels: ["bug", "priority::high"]
              - title: "Everything"
                scope: global
            """,
        )

        config = load_config(config_path)

        assert [section.title for section in config.sections] == [
            "My Reviews",
            "Team MRs",
            "Everything",
        ]

        first, second, third = config.sections
        assert first.scope == Scope.PROJECT
        assert first.project == "group/project-path"
        assert first.state == MergeRequestState.OPENED
        assert first.labels == []

        assert second.scope == Scope.GROUP
        assert second.group == "group-path"
        assert second.state == MergeRequestState.MERGED
        assert second.author == "@me"
        assert second.assignee == "someone"
        assert second.labels == ["bug", "priority::high"]

        assert third.scope == Scope.GLOBAL
        assert third.project is None
        assert third.group is None

    def test_refresh_interval_defaults_to_60(self, tmp_path: Path) -> None:
        config_path = write_config(
            tmp_path / "config.yml",
            'sections:\n  - {title: "All", scope: global}\n',
        )

        config = load_config(config_path)

        assert config.refresh_interval == 60

    def test_refresh_interval_parses_when_present(self, tmp_path: Path) -> None:
        config_path = write_config(
            tmp_path / "config.yml",
            'refresh_interval: 30\nsections:\n  - {title: "All", scope: global}\n',
        )

        config = load_config(config_path)

        assert config.refresh_interval == 30

    def test_token_parses_when_present(self, tmp_path: Path) -> None:
        config_path = write_config(
            tmp_path / "config.yml",
            'token: "glpat-abc123"\nsections:\n  - {title: "All", scope: global}\n',
        )

        config = load_config(config_path)

        assert config.token == "glpat-abc123"

    def test_missing_required_field_raises_config_error(self, tmp_path: Path) -> None:
        config_path = write_config(
            tmp_path / "config.yml",
            "sections:\n  - {scope: global}\n",
        )

        with pytest.raises(ConfigError):
            load_config(config_path)

    def test_bad_scope_value_raises_config_error(self, tmp_path: Path) -> None:
        config_path = write_config(
            tmp_path / "config.yml",
            'sections:\n  - {title: "All", scope: nonsense}\n',
        )

        with pytest.raises(ConfigError):
            load_config(config_path)

    def test_bad_state_value_raises_config_error(self, tmp_path: Path) -> None:
        config_path = write_config(
            tmp_path / "config.yml",
            'sections:\n  - {title: "All", scope: global, state: nonsense}\n',
        )

        with pytest.raises(ConfigError):
            load_config(config_path)

    def test_project_scope_missing_project_key_raises_config_error(self, tmp_path: Path) -> None:
        config_path = write_config(
            tmp_path / "config.yml",
            'sections:\n  - {title: "My Reviews", scope: project}\n',
        )

        with pytest.raises(ConfigError):
            load_config(config_path)

    def test_group_scope_missing_group_key_raises_config_error(self, tmp_path: Path) -> None:
        config_path = write_config(
            tmp_path / "config.yml",
            'sections:\n  - {title: "Team MRs", scope: group}\n',
        )

        with pytest.raises(ConfigError):
            load_config(config_path)

    def test_no_sections_raises_config_error(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path / "config.yml", "sections: []\n")

        with pytest.raises(ConfigError):
            load_config(config_path)

    def test_missing_file_raises_config_error(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError):
            load_config(tmp_path / "missing.yml")


class TestResolveConfigPath:
    def test_prefers_repo_local_config_when_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        repo_local = write_config(tmp_path / ".glab-dash.yml", "sections: []\n")

        resolved = resolve_config_path(env={})

        assert resolved == repo_local

    def test_falls_back_to_xdg_config_home(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        xdg_home = tmp_path / "xdg"
        xdg_home.mkdir()

        resolved = resolve_config_path(env={"XDG_CONFIG_HOME": str(xdg_home)})

        assert resolved == xdg_home / "glab-dash" / "config.yml"

    def test_falls_back_to_home_config_dir_when_no_xdg_config_home(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))

        resolved = resolve_config_path(env={})

        assert resolved == tmp_path / ".config" / "glab-dash" / "config.yml"
