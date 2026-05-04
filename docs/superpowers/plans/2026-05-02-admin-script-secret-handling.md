# Admin Script Secret Handling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove hardcoded administrator passwords from maintenance scripts while preserving both automation and terminal-based usage.

**Architecture:** Add a small shared helper in `scripts/` for environment-variable lookup, hidden password prompting, and user lookup. Update the admin maintenance scripts to consume that helper, keep `list_users.py` unchanged, and add focused regression tests around non-secret handling and verification behavior.

**Tech Stack:** Python 3, `getpass`, existing `AuthDBService`, `pytest`, `monkeypatch`

---

### Task 1: Add shared script helpers

**Files:**
- Create: `scripts/admin_script_utils.py`
- Test: `tests/test_admin_script_utils.py`

- [ ] **Step 1: Write the failing test**

```python
from scripts.admin_script_utils import get_env_value, require_password_value


def test_get_env_value_returns_default_for_blank(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "   ")
    assert get_env_value("ADMIN_USERNAME", default="admin") == "admin"


def test_require_password_value_uses_env(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "Secret123!")
    assert require_password_value("ADMIN_PASSWORD", "Prompt") == "Secret123!"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin_script_utils.py -v`
Expected: FAIL with import or symbol errors because `scripts/admin_script_utils.py` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
import getpass
import os


def get_env_value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def require_password_value(name: str, prompt: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        value = getpass.getpass(prompt)
    value = value.strip()
    if not value:
        raise ValueError(f"{name} cannot be empty")
    return value
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_admin_script_utils.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/admin_script_utils.py tests/test_admin_script_utils.py
git commit -m "refactor(scripts): add shared admin secret helpers"
```

### Task 2: Update create and reset scripts

**Files:**
- Modify: `scripts/create_admin.py`
- Modify: `scripts/reset_admin_password.py`
- Modify: `scripts/admin_script_utils.py`
- Test: `tests/test_admin_script_utils.py`

- [ ] **Step 1: Write the failing tests**

```python
from scripts.admin_script_utils import find_user_by_username


class DummyDB:
    def list_users(self):
        return [{"username": "Admin", "user_id": "u1"}]


def test_find_user_by_username_is_case_insensitive():
    assert find_user_by_username(DummyDB(), "admin") == {"username": "Admin", "user_id": "u1"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin_script_utils.py -v`
Expected: FAIL because `find_user_by_username` is not implemented.

- [ ] **Step 3: Write minimal implementation**

```python
from app.services.auth_db import AuthDBService


def find_user_by_username(db: AuthDBService, username: str) -> dict | None:
    normalized = username.strip().lower()
    for user in db.list_users():
        if str(user.get("username", "")).strip().lower() == normalized:
            return user
    return None
```

Update the scripts to:

```python
username = get_env_value("ADMIN_USERNAME", default="admin") or "admin"
role = get_env_value("ADMIN_ROLE", default="admin") or "admin"
password = require_password_value("ADMIN_PASSWORD", f"Enter password for {username}: ")
```

and:

```python
username = get_env_value("ADMIN_USERNAME", default="admin") or "admin"
new_password = require_password_value("ADMIN_NEW_PASSWORD", f"Enter new password for {username}: ")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_admin_script_utils.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/create_admin.py scripts/reset_admin_password.py scripts/admin_script_utils.py tests/test_admin_script_utils.py
git commit -m "refactor(scripts): remove hardcoded admin passwords"
```

### Task 3: Update verify-and-reset flow

**Files:**
- Modify: `scripts/test_and_reset_admin.py`
- Modify: `scripts/admin_script_utils.py`
- Create: `tests/test_admin_maintenance_scripts.py`

- [ ] **Step 1: Write the failing tests**

```python
from scripts.admin_script_utils import should_verify_current_password


def test_should_verify_current_password_only_when_present(monkeypatch):
    monkeypatch.delenv("ADMIN_CURRENT_PASSWORD", raising=False)
    assert should_verify_current_password() is False
    monkeypatch.setenv("ADMIN_CURRENT_PASSWORD", "Secret123!")
    assert should_verify_current_password() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin_maintenance_scripts.py -v`
Expected: FAIL because the helper and test file do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def should_verify_current_password() -> bool:
    current_password = os.getenv("ADMIN_CURRENT_PASSWORD")
    return bool(current_password and current_password.strip())
```

Update `scripts/test_and_reset_admin.py` to:

```python
current_password = get_env_value("ADMIN_CURRENT_PASSWORD")
if current_password:
    result = db.user_manager.authenticate(username, current_password)
    if not result:
        print("Current password verification failed.")
        return 1
```

and reset with:

```python
new_password = require_password_value("ADMIN_NEW_PASSWORD", f"Enter new password for {username}: ")
```

After reset, authenticate with `new_password` and print a success or warning message without echoing the password.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_admin_maintenance_scripts.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/test_and_reset_admin.py scripts/admin_script_utils.py tests/test_admin_maintenance_scripts.py
git commit -m "refactor(scripts): harden admin password reset flow"
```

### Task 4: Validate end-to-end behavior

**Files:**
- Modify: `scripts/create_admin.py`
- Modify: `scripts/reset_admin_password.py`
- Modify: `scripts/test_and_reset_admin.py`
- Modify: `tests/test_admin_maintenance_scripts.py`

- [ ] **Step 1: Add focused behavior tests**

```python
def test_empty_password_from_prompt_raises(monkeypatch):
    monkeypatch.delenv("ADMIN_NEW_PASSWORD", raising=False)
    monkeypatch.setattr("getpass.getpass", lambda _prompt: "   ")
    with pytest.raises(ValueError):
        require_password_value("ADMIN_NEW_PASSWORD", "Prompt")
```

- [ ] **Step 2: Run targeted test suite**

Run: `pytest tests/test_admin_script_utils.py tests/test_admin_maintenance_scripts.py -v`
Expected: PASS

- [ ] **Step 3: Do a script smoke check**

Run: `python -m compileall scripts`
Expected: `Compiling 'scripts\\...'` lines with no syntax errors

- [ ] **Step 4: Review user-facing output**

Confirm the scripts no longer print password values on success and still clearly report:

```text
Admin user 'admin' already exists.
Admin password reset successfully!
Password reset successful!
Verification: Login successful with new password!
```

- [ ] **Step 5: Commit**

```bash
git add scripts tests
git commit -m "test(scripts): cover secure admin maintenance flows"
```
