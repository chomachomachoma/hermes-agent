"""Tests for gateway.dashboard_conversations.post_new_conversation."""

import pytest

from hermes_state import SessionDB


@pytest.fixture()
def db(tmp_path):
    session_db = SessionDB(db_path=tmp_path / "state.db")
    yield session_db
    session_db.close()


def test_creates_titled_session_with_message(db):
    from gateway.dashboard_conversations import post_new_conversation

    result = post_new_conversation("Daily Report — 2026-07-07", "hello world", db=db)

    assert set(result) == {"session_id", "title"}
    sid = result["session_id"]
    assert result["title"] == "Daily Report — 2026-07-07"

    session = db.get_session(sid)
    assert session is not None
    assert db.get_session_title(sid) == "Daily Report — 2026-07-07"

    msgs = db.get_messages(sid)
    assert len(msgs) == 1
    only = msgs[0]
    role = only.get("role") if isinstance(only, dict) else only.role
    content = only.get("content") if isinstance(only, dict) else only.content
    assert role == "user"
    assert content == "hello world"


def test_each_call_creates_distinct_session(db):
    from gateway.dashboard_conversations import post_new_conversation

    a = post_new_conversation("Same Title", "first", db=db)
    b = post_new_conversation("Same Title", "second", db=db)
    assert a["session_id"] != b["session_id"]


def test_source_defaults_to_api_server(db):
    from gateway.dashboard_conversations import post_new_conversation

    sid = post_new_conversation("T", "m", db=db)["session_id"]
    session = db.get_session(sid)
    source = session.get("source") if isinstance(session, dict) else session.source
    assert source == "api_server"


def test_empty_title_falls_back_to_default(db):
    from gateway.dashboard_conversations import post_new_conversation

    result = post_new_conversation("", "m", db=db)
    assert result["title"] == "New conversation"
    assert db.get_session_title(result["session_id"]) == "New conversation"


def test_empty_message_creates_conversation_without_message(db):
    from gateway.dashboard_conversations import post_new_conversation

    result = post_new_conversation("Title Only", "", db=db)
    assert db.get_session(result["session_id"]) is not None
    assert db.get_messages(result["session_id"]) == []
