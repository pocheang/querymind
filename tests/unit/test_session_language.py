"""Tests for session language tracking service."""

import pytest

from app.services.session_language import (
    clear_all_history,
    clear_session_history,
    get_language_history,
    get_language_preference,
    update_language_history,
)


@pytest.fixture(autouse=True)
def clean_history():
    """Clear all history before and after each test."""
    clear_all_history()
    yield
    clear_all_history()


def test_update_language_history_basic():
    """Test basic language history update."""
    session_id = "test_session_1"

    update_language_history(session_id, "zh")
    history = get_language_history(session_id)

    assert history == ["zh"]


def test_update_language_history_multiple():
    """Test multiple language updates."""
    session_id = "test_session_2"

    update_language_history(session_id, "zh")
    update_language_history(session_id, "en")
    update_language_history(session_id, "zh")

    history = get_language_history(session_id)
    assert history == ["zh", "en", "zh"]


def test_update_language_history_keeps_last_5():
    """Test that only last 5 languages are kept."""
    session_id = "test_session_3"

    for i in range(10):
        lang = "zh" if i % 2 == 0 else "en"
        update_language_history(session_id, lang)

    history = get_language_history(session_id)
    assert len(history) == 5
    # Last 5 should be: en, zh, en, zh, en (indices 5-9)
    assert history == ["en", "zh", "en", "zh", "en"]


def test_get_language_preference_default():
    """Test default language preference for new session."""
    session_id = "test_session_4"

    preference = get_language_preference(session_id)
    assert preference == "zh"


def test_get_language_preference_single_language():
    """Test language preference with single language."""
    session_id = "test_session_5"

    update_language_history(session_id, "en")
    preference = get_language_preference(session_id)

    assert preference == "en"


def test_get_language_preference_majority():
    """Test language preference returns majority language."""
    session_id = "test_session_6"

    # Add 3 Chinese and 2 English
    update_language_history(session_id, "zh")
    update_language_history(session_id, "en")
    update_language_history(session_id, "zh")
    update_language_history(session_id, "en")
    update_language_history(session_id, "zh")

    preference = get_language_preference(session_id)
    assert preference == "zh"


def test_get_language_preference_tie():
    """Test language preference with tie (should return first in counter)."""
    session_id = "test_session_7"

    # Add 2 Chinese and 2 English
    update_language_history(session_id, "zh")
    update_language_history(session_id, "en")
    update_language_history(session_id, "zh")
    update_language_history(session_id, "en")

    preference = get_language_preference(session_id)
    # Counter.most_common() returns the first one encountered in case of tie
    assert preference in ["zh", "en"]


def test_clear_session_history():
    """Test clearing history for specific session."""
    session_id_1 = "test_session_8"
    session_id_2 = "test_session_9"

    update_language_history(session_id_1, "zh")
    update_language_history(session_id_2, "en")

    clear_session_history(session_id_1)

    assert get_language_history(session_id_1) == []
    assert get_language_history(session_id_2) == ["en"]


def test_clear_all_history():
    """Test clearing all session history."""
    update_language_history("session_1", "zh")
    update_language_history("session_2", "en")
    update_language_history("session_3", "fr")

    clear_all_history()

    assert get_language_history("session_1") == []
    assert get_language_history("session_2") == []
    assert get_language_history("session_3") == []


def test_update_language_history_empty_session_id():
    """Test that empty session_id is handled gracefully."""
    update_language_history("", "zh")

    # Should not crash, but also should not store anything
    history = get_language_history("")
    assert history == []


def test_update_language_history_empty_language():
    """Test that empty language is handled gracefully."""
    session_id = "test_session_10"

    update_language_history(session_id, "")

    # Should not crash, but also should not store anything
    history = get_language_history(session_id)
    assert history == []


def test_get_language_preference_empty_session_id():
    """Test that empty session_id returns default."""
    preference = get_language_preference("")
    assert preference == "zh"


def test_multiple_sessions_isolated():
    """Test that multiple sessions are isolated from each other."""
    session_1 = "test_session_11"
    session_2 = "test_session_12"

    update_language_history(session_1, "zh")
    update_language_history(session_1, "zh")
    update_language_history(session_1, "zh")

    update_language_history(session_2, "en")
    update_language_history(session_2, "en")

    assert get_language_preference(session_1) == "zh"
    assert get_language_preference(session_2) == "en"
    assert get_language_history(session_1) == ["zh", "zh", "zh"]
    assert get_language_history(session_2) == ["en", "en"]


def test_language_preference_updates_with_new_data():
    """Test that language preference changes as new data comes in."""
    session_id = "test_session_13"

    # Start with Chinese majority
    update_language_history(session_id, "zh")
    update_language_history(session_id, "zh")
    update_language_history(session_id, "en")

    assert get_language_preference(session_id) == "zh"

    # Add more English to shift preference
    update_language_history(session_id, "en")
    update_language_history(session_id, "en")

    assert get_language_preference(session_id) == "en"

    # Verify only last 5 are kept
    history = get_language_history(session_id)
    assert len(history) == 5
    assert history == ["zh", "zh", "en", "en", "en"]
