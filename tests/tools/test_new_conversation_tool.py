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

    entry = _get_entry()
    result = json.loads(entry.handler({"title": "Tool Test", "message": "hi"}))
    assert result.get("success") is True
    sid = result["session_id"]

    db = SessionDB()
    try:
        assert db.get_session(sid) is not None
        assert db.get_session_title(sid) == "Tool Test"
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
