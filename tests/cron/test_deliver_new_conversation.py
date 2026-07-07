"""deliver="new_conversation" routes cron output into a fresh dashboard conversation."""

from hermes_state import SessionDB


def _job(**over):
    job = {
        "id": "testjob123456",
        "name": "Nightly Report",
        "deliver": "new_conversation",
        "origin": {"platform": "api_server", "chat_id": "dash_original"},
    }
    job.update(over)
    return job


def _api_server_sessions(db):
    return [s for s in db.list_sessions_rich(source="api_server", limit=200)]


def test_new_conversation_delivery_creates_fresh_session():
    from cron.scheduler import _deliver_result

    db = SessionDB()
    try:
        before = {s["id"] for s in _api_server_sessions(db)}
        result = _deliver_result(_job(), "the report body")
        assert result is None  # None == delivered

        after = _api_server_sessions(db)
        new = [s for s in after if s["id"] not in before]
        assert len(new) == 1
        new_session = new[0]
        assert new_session["id"].startswith("conv_")
        title = db.get_session_title(new_session["id"])
        assert title.startswith("Nightly Report — 20")  # "<name> — <YYYY-MM-DD>"

        msgs = db.get_messages(new_session["id"])
        assert len(msgs) == 1
        content = msgs[0].get("content") if isinstance(msgs[0], dict) else msgs[0].content
        assert "the report body" in content
    finally:
        db.close()


def test_origin_session_is_untouched():
    from cron.scheduler import _deliver_result

    db = SessionDB()
    try:
        db.create_session("dash_original", "api_server")
        assert _deliver_result(_job(), "body") is None
        assert db.get_messages("dash_original") == []
    finally:
        db.close()


def test_failure_returns_error_string(monkeypatch):
    import gateway.dashboard_conversations as dc
    from cron import scheduler

    def boom(*a, **kw):
        raise RuntimeError("db exploded")

    monkeypatch.setattr(dc, "post_new_conversation", boom)
    result = scheduler._deliver_result(_job(), "body")
    assert isinstance(result, str)
    assert "db exploded" in result


def test_empty_name_falls_back_to_job_id():
    from cron.scheduler import _deliver_result

    db = SessionDB()
    try:
        before = {s["id"] for s in _api_server_sessions(db)}
        assert _deliver_result(_job(name=""), "body") is None

        new = [s for s in _api_server_sessions(db) if s["id"] not in before]
        assert len(new) == 1
        title = db.get_session_title(new[0]["id"])
        assert title.startswith("testjob123456 — 20")
    finally:
        db.close()


def test_other_deliver_modes_unaffected():
    from cron.scheduler import _deliver_result

    # deliver=local returns None without creating any api_server session.
    db = SessionDB()
    try:
        before = len(_api_server_sessions(db))
        assert _deliver_result(_job(deliver="local"), "body") is None
        assert len(_api_server_sessions(db)) == before
    finally:
        db.close()
