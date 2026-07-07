"""Tests for the post_new_conversation agent tool registration and handler."""

import json


def _get_entry():
    import tools.new_conversation_tool  # noqa: F401 — import registers the tool
    from tools.registry import registry

    entry = registry._tools.get("post_new_conversation")
    assert entry is not None, "tool not registered"
    return entry


def test_tool_registered_in_conversations_toolset():
    entry = _get_entry()
    assert entry.toolset == "conversations"
    assert entry.schema["name"] == "post_new_conversation"
    params = entry.schema["parameters"]
    assert set(params["required"]) == {"title", "message"}


def test_handler_creates_conversation(tmp_path):
    from hermes_state import SessionDB
    import uuid

    entry = _get_entry()
    # Unique title per invocation: hermes_state.DEFAULT_DB_PATH is frozen at
    # module-import time, so in multi-file pytest runs (unsupported here —
    # the repo's runner spawns one subprocess per test file, see
    # tests/conftest.py "per-file process isolation") the default SessionDB
    # can point at a shared DB where a fixed title would collide with prior
    # runs and get auto-disambiguated. A unique title keeps this test
    # meaningful in both run modes.
    title = f"Tool Test {uuid.uuid4().hex[:8]}"
    result = json.loads(entry.handler({"title": title, "message": "hi"}))
    assert result.get("success") is True
    assert result["title"] == title
    sid = result["session_id"]

    db = SessionDB()
    try:
        assert db.get_session(sid) is not None
        assert db.get_session_title(sid) == title
    finally:
        db.close()


def test_handler_missing_title_errors():
    entry = _get_entry()
    result = json.loads(entry.handler({"message": "hi"}))
    assert "error" in result


def test_toolset_declared():
    from toolsets import TOOLSETS

    assert "conversations" in TOOLSETS
    assert "post_new_conversation" in TOOLSETS["conversations"]["tools"]
