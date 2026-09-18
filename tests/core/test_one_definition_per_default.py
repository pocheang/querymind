"""Two statements of one default, where only one of them is read.

Both cases here are latent -- nothing is broken today -- and both are the shape
that stops being latent the moment somebody reads the wrong one of the two.

**`TimeoutConfig`'s defaults claimed to mirror `Settings.stage_timeout_*`** in a
docstring, and `retrieval_timeout_ms` was 15_000 against a field default of
30_000. `from_settings` always supplies the value, so nothing ran on 15s -- but
it is the number a reader takes from the class rather than from the field, and a
stated correspondence that is false is worse than none.

**`APP_ENV` had three spellings and no agreement between them.**
`Settings.app_env` defaulted to `"dev"` while `resolve_runtime_env_file`
defaulted to `"development"`; that function mapped `dev` but knew nothing about
`prod`; and two consumers tested `{"prod", "production"}` while the render step
writes only the long forms.

`APP_ENV=prod` is where that combination bites. `resolve_runtime_env_file` looked
for `.runtime/prod.env`, which `deploy/scripts/config.py` never writes, found
nothing, and left `Settings` on its hardcoded defaults -- while `factory.py`'s
CORS guard and `validate_security_settings` both read the value as production. A
deployment naming itself the short way ran entirely on defaults, in production,
with nothing reporting it.

`normalise_environment_name` is the one answer now, and `Settings` carries the
normalised form, so a consumer compares against one string.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.core.config import DEFAULT_ENVIRONMENT, Settings, normalise_environment_name, resolve_runtime_env_file
from app.orchestration.timeout_control import TimeoutConfig

MIRRORED = {
    "total_timeout_ms": "stage_timeout_total_ms",
    "route_timeout_ms": "stage_timeout_route_ms",
    "plan_timeout_ms": "stage_timeout_plan_ms",
    "retrieval_timeout_ms": "stage_timeout_retrieval_ms",
    "tool_timeout_ms": "stage_timeout_tool_ms",
    "synthesis_timeout_ms": "stage_timeout_synthesis_ms",
    "finalization_timeout_ms": "stage_timeout_finalization_ms",
    "overhead_buffer_ms": "stage_timeout_overhead_ms",
}


# --- the timeout defaults -------------------------------------------------


@pytest.mark.parametrize(("attribute", "field"), sorted(MIRRORED.items()))
def test_timeout_defaults_mirror_settings(attribute, field):
    """The docstring's claim, enforced instead of restated."""

    assert getattr(TimeoutConfig(), attribute) == getattr(Settings(), field)


def test_every_timeout_field_is_covered_by_that_mirror():
    """Otherwise a ninth stage could be added to one side and not the other, and
    the parametrized check above would pass by not looking at it."""

    declared = {name for name in TimeoutConfig.__dataclass_fields__ if name.endswith(("_timeout_ms", "_buffer_ms"))}

    assert declared == set(MIRRORED)


def test_the_bare_defaults_still_fit_the_total():
    """Raising retrieval from 15s to 30s moves the sum; it has to stay legal."""

    TimeoutConfig().validate()


# --- the environment name -------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("dev", "development"),
        ("DEV", "development"),
        (" Dev ", "development"),
        ("prod", "production"),
        ("PROD", "production"),
        ("development", "development"),
        ("production", "production"),
        ("test", "test"),
        ("", "development"),
        (None, "development"),
    ],
)
def test_the_environment_name_has_one_spelling(raw, expected):
    assert normalise_environment_name(raw) == expected


def test_settings_carries_the_normalised_form(monkeypatch):
    """So a consumer compares against one string rather than a set of spellings."""

    assert Settings(APP_ENV="prod").app_env == "production"
    assert Settings(APP_ENV="dev").app_env == "development"


def test_the_field_default_and_the_file_lookup_default_agree():
    """They were `"dev"` and `"development"`: two defaults for one concept.

    Asserted on the **declared** default rather than on `Settings().app_env`. The
    first version of this test did the latter and could not fail: the normaliser
    turns a declared `"dev"` into `"development"` on the way out, so the field
    could go on stating a second default and the value would agree anyway. That is
    the vacuous assertion this repository keeps recording -- found by putting
    `"dev"` back and watching nothing redden.
    """

    assert Settings.model_fields["app_env"].default == DEFAULT_ENVIRONMENT
    assert normalise_environment_name(DEFAULT_ENVIRONMENT) == DEFAULT_ENVIRONMENT


def test_a_short_name_finds_the_file_the_render_step_writes(monkeypatch, tmp_path):
    """The failure underneath all of this.

    `APP_ENV=prod` looked for `.runtime/prod.env`. Nothing writes that name, so
    the process ran on defaults while calling itself production.
    """

    runtime = tmp_path / ".runtime"
    runtime.mkdir()
    (runtime / "production.env").write_text("TOP_K=7\n", encoding="utf-8")
    monkeypatch.delenv("RUNTIME_ENV_FILE", raising=False)
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setattr("app.core.config.Path", _PathRootedAt(tmp_path))

    assert resolve_runtime_env_file() == str(runtime / "production.env")


class _PathRootedAt:
    """`resolve_runtime_env_file` walks up from `__file__`; point that at tmp_path.

    Patching the lookup rather than the repository's own `.runtime/` keeps the
    test from depending on -- or creating -- a gitignored file in the checkout.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def __call__(self, value):
        if str(value).replace("\\", "/").endswith("app/core/config.py"):
            return _FakeConfigPath(self._root)
        return Path(value)


class _FakeConfigPath:
    def __init__(self, root: Path) -> None:
        self._root = root

    def resolve(self):
        return self

    @property
    def parents(self):
        return {2: self._root}


def test_an_unrecognised_environment_is_left_alone():
    """`staging` is not in the render step's set, but a hand-rendered
    `.runtime/staging.env` works today; normalising spelling must not become
    forbidding names."""

    assert normalise_environment_name("staging") == "staging"
    assert Settings(APP_ENV="staging").app_env == "staging"


def test_the_long_names_are_the_ones_the_render_step_validates():
    """The set this normalises *towards*, read from the render step rather than repeated."""

    module = ast.parse(Path("deploy/scripts/config.py").read_text(encoding="utf-8"))
    valid = next(
        {element.value for element in node.value.elts}
        for node in ast.walk(module)
        if isinstance(node, ast.Assign)
        and any(getattr(target, "id", None) == "VALID_ENVIRONMENTS" for target in node.targets)
        and isinstance(node.value, ast.Set)
    )

    assert {normalise_environment_name(name) for name in ("dev", "prod", "test")} <= valid
    assert DEFAULT_ENVIRONMENT in valid
