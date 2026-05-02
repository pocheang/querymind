import pytest

from scripts.admin_script_utils import (
    find_user_by_username,
    get_env_value,
    require_password_value,
    should_verify_current_password,
)


class DummyDB:
    def list_users(self):
        return [{"username": "Admin", "user_id": "u1"}]


def test_get_env_value_returns_default_for_blank(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "   ")
    assert get_env_value("ADMIN_USERNAME", default="admin") == "admin"


def test_require_password_value_uses_env(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "Secret123!")
    assert require_password_value("ADMIN_PASSWORD", "Prompt") == "Secret123!"


def test_find_user_by_username_is_case_insensitive():
    assert find_user_by_username(DummyDB(), "admin") == {"username": "Admin", "user_id": "u1"}


def test_should_verify_current_password_only_when_present(monkeypatch):
    monkeypatch.delenv("ADMIN_CURRENT_PASSWORD", raising=False)
    assert should_verify_current_password() is False

    monkeypatch.setenv("ADMIN_CURRENT_PASSWORD", "Secret123!")
    assert should_verify_current_password() is True


def test_require_password_value_rejects_blank_prompt(monkeypatch):
    monkeypatch.delenv("ADMIN_NEW_PASSWORD", raising=False)
    monkeypatch.setattr("getpass.getpass", lambda _prompt: "   ")
    with pytest.raises(ValueError):
        require_password_value("ADMIN_NEW_PASSWORD", "Prompt")
