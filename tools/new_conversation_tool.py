"""
post_new_conversation — agent tool to start a fresh dashboard conversation.

Thin wrapper over gateway.dashboard_conversations.post_new_conversation.
Use it to publish reports/briefs as their own conversation so long-running
sessions don't accumulate unbounded context and fresh items sort to the top
of the dashboard list.
"""

import json
import logging

logger = logging.getLogger(__name__)

POST_NEW_CONVERSATION_SCHEMA = {
    "name": "post_new_conversation",
    "description": (
        "Create a NEW dashboard conversation and post a message into it. "
        "Use this to publish a report, summary, or briefing as its own "
        "conversation instead of appending to the current one — each call "
        "creates a fresh conversation that appears at the top of the "
        "dashboard's conversation list. Returns the new session_id. "
        "Do NOT use this for replies in the current conversation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Conversation title shown in the dashboard list, e.g. 'Daily WP Plugin Research — 2026-07-08'.",
            },
            "message": {
                "type": "string",
                "description": "The content to post as the conversation's first message (markdown ok).",
            },
            "model": {
                "type": "string",
                "description": "Optional model name to record on the new session (defaults to the server's default).",
            },
        },
        "required": ["title", "message"],
    },
}


def _handle(args: dict, **kw) -> str:
    from tools.registry import tool_error

    title = (args.get("title") or "").strip()
    message = args.get("message") or ""
    if not title:
        return tool_error("title is required")
    if not str(message).strip():
        return tool_error("message is required")
    try:
        from gateway.dashboard_conversations import post_new_conversation

        result = post_new_conversation(title, str(message), model=args.get("model"))
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as e:
        logger.debug("post_new_conversation tool failed", exc_info=True)
        return tool_error(f"failed to post new conversation: {e}")


def check_new_conversation_requirements() -> bool:
    """SessionDB is core — the tool is available wherever hermes_state imports."""
    try:
        import hermes_state  # noqa: F401
        return True
    except Exception:
        return False


from tools.registry import registry

registry.register(
    name="post_new_conversation",
    toolset="conversations",
    schema=POST_NEW_CONVERSATION_SCHEMA,
    handler=_handle,
    check_fn=check_new_conversation_requirements,
    emoji="🗣️",
)
