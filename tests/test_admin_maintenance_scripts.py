from scripts.admin_script_utils import should_verify_current_password


def test_should_verify_current_password_only_when_present(monkeypatch):
    monkeypatch.delenv("ADMIN_CURRENT_PASSWORD", raising=False)
    assert should_verify_current_password() is False

    monkeypatch.setenv("ADMIN_CURRENT_PASSWORD", "Secret123!")
    assert should_verify_current_password() is True
