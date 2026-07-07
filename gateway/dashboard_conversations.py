"""
Dashboard conversation factory.

One deep-module entry point for "create a fresh dashboard conversation and
post a message into it".  Consumers: the ``post_new_conversation`` agent tool
(tools/new_conversation_tool.py) and the cron ``deliver: "new_conversation"``
mode (cron/scheduler.py::_deliver_result).  Callers never touch SessionDB
directly — the id scheme, title handling, and role convention live here.

Sessions are created with ``source="api_server"`` so they show up in the
dashboard's conversation list (GET /api/sessions -> list_sessions_rich, which
orders by last-active — a fresh conversation sorts to the top).

Messages are stored ``role="user"``: the posted content is not the agent of
the *new* session speaking, and a user-role seed keeps the transcript safe on
strict-alternation providers when the user later replies in the conversation
(same convention as cron/scheduler._seed_cron_thread_session).
"""

import logging
import re
import time
import uuid

logger = logging.getLogger(__name__)

DEFAULT_TITLE = "New conversation"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(title: str, max_len: int = 32) -> str:
    slug = _SLUG_RE.sub("-", title.lower()).strip("-")
    return slug[:max_len] or "conversation"


def post_new_conversation(
    title: str,
    message: str,
    *,
    model: str = None,
    source: str = "api_server",
    role: str = "user",
    db=None,
) -> dict:
    """Create a new dashboard conversation and post ``message`` into it.

    Returns ``{"session_id": <new id>, "title": <effective title>}``.
    Raises ``RuntimeError`` if the session cannot be created.  An empty
    ``message`` still creates the (titled) conversation; an empty ``title``
    falls back to ``DEFAULT_TITLE``.

    ``db`` is injectable for tests; by default a fresh SessionDB is opened
    and closed around the writes (cron delivery runs out-of-process, so a
    long-lived handle would hold the sqlite file open for no reason).
    """
    effective_title = (title or "").strip() or DEFAULT_TITLE
    suffix = uuid.uuid4().hex[:8]
    session_id = f"conv_{_slugify(effective_title)}_{int(time.time())}_{suffix}"

    owns_db = db is None
    if owns_db:
        from hermes_state import SessionDB
        db = SessionDB()
    try:
        try:
            db.create_session(session_id, source, model=model)
        except Exception as e:
            raise RuntimeError(f"failed to create conversation: {e}") from e

        try:
            db.set_session_title(session_id, effective_title)
        except ValueError:
            # SessionDB enforces globally-unique titles. Callers legitimately
            # create multiple conversations with the same title (e.g. a cron
            # job repeatedly delivering a "Daily Report") - disambiguate
            # rather than fail the whole conversation. `suffix` is already
            # part of session_id, so it's guaranteed unique.
            effective_title = f"{effective_title} ({suffix})"
            try:
                db.set_session_title(session_id, effective_title)
            except Exception as e:
                raise RuntimeError(f"failed to set conversation title: {e}") from e
        except Exception as e:
            raise RuntimeError(f"failed to create conversation: {e}") from e

        if (message or "").strip():
            try:
                db.append_message(session_id=session_id, role=role, content=message)
            except Exception as e:
                raise RuntimeError(
                    f"conversation {session_id} created but posting the message failed: {e}"
                ) from e
        logger.info("Posted new dashboard conversation %s (%r)", session_id, effective_title)
        return {"session_id": session_id, "title": effective_title}
    finally:
        if owns_db:
            try:
                db.close()
            except Exception:
                pass
