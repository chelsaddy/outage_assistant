"""Persistence for one conversation: the agent_steps log, and the history rebuilt from it.

Every user message, model response, tool call, tool result and escalation is written to
agent_steps, in order. That log is both the audit trail the dashboard shows and the source of
the message history sent back to the model on the next turn (append-only, so the model's
earlier responses, including thinking blocks, are replayed exactly as they were returned).
"""
from psycopg.types.json import Jsonb

from app.helpers import db


class ConversationNotFound(Exception):
    pass


class ConversationStore:
    def __init__(self, conversation_id: int):
        self.conversation_id = conversation_id

    # --- lifecycle ---------------------------------------------------------------------

    @classmethod
    def open(cls, conversation_id: int | None) -> "ConversationStore":
        with db() as conn:
            if conversation_id is None:
                conversation_id = conn.execute(
                    "INSERT INTO conversations DEFAULT VALUES RETURNING id"
                ).fetchone()["id"]
            elif conn.execute("SELECT 1 FROM conversations WHERE id = %s", (conversation_id,)).fetchone() is None:
                raise ConversationNotFound(conversation_id)
        return cls(conversation_id)

    def _get(self, column: str):
        with db() as conn:
            return conn.execute(
                f"SELECT {column} AS v FROM conversations WHERE id = %s", (self.conversation_id,)
            ).fetchone()["v"]

    def status(self) -> str:
        return self._get("status")

    def customer_id(self) -> int | None:
        return self._get("customer_id")

    def set_customer(self, customer_id: int) -> None:
        with db() as conn:
            conn.execute("UPDATE conversations SET customer_id = %s WHERE id = %s",
                         (customer_id, self.conversation_id))

    def escalate(self, reason: str, summary: str, ticket_id: int | None) -> None:
        with db() as conn:
            conn.execute("UPDATE conversations SET status = 'escalated' WHERE id = %s", (self.conversation_id,))
        self.log("escalation", {"reason": reason, "summary": summary, "ticket_id": ticket_id})

    # --- the step log ------------------------------------------------------------------

    def log(self, kind: str, payload: dict, tool_name: str | None = None) -> dict:
        with db() as conn:
            return conn.execute(
                """
                INSERT INTO agent_steps (conversation_id, step_no, kind, tool_name, payload)
                VALUES (%(cid)s,
                        (SELECT coalesce(max(step_no), 0) + 1 FROM agent_steps WHERE conversation_id = %(cid)s),
                        %(kind)s, %(tool)s, %(payload)s)
                RETURNING step_no, kind, tool_name, payload, created_at
                """,
                {"cid": self.conversation_id, "kind": kind, "tool": tool_name, "payload": Jsonb(payload)},
            ).fetchone()

    def steps(self, after_step: int = 0) -> list[dict]:
        with db() as conn:
            return conn.execute(
                """
                SELECT step_no, kind, tool_name, payload, created_at FROM agent_steps
                WHERE conversation_id = %s AND step_no > %s ORDER BY step_no
                """,
                (self.conversation_id, after_step),
            ).fetchall()

    def last_step_no(self) -> int:
        with db() as conn:
            return conn.execute(
                "SELECT coalesce(max(step_no), 0) AS n FROM agent_steps WHERE conversation_id = %s",
                (self.conversation_id,),
            ).fetchone()["n"]

    def history(self) -> list[dict]:
        """Rebuild the Messages API history from the step log.

        user_message      -> user turn (text)
        assistant_message -> assistant turn (content blocks exactly as the API returned them)
        tool_result       -> consecutive results grouped into one user turn
        tool_call / escalation steps are for the trace only (the call is already inside the
        assistant content).
        """
        messages: list[dict] = []
        for step in self.steps():
            p = step["payload"]
            if step["kind"] == "user_message":
                messages.append({"role": "user", "content": p["text"]})
            elif step["kind"] == "assistant_message":
                messages.append({"role": "assistant", "content": p["content"]})
            elif step["kind"] == "tool_result":
                block = {"type": "tool_result", "tool_use_id": p["tool_use_id"],
                         "content": p["content"], "is_error": p["is_error"]}
                last = messages[-1] if messages else None
                if last and last["role"] == "user" and isinstance(last["content"], list) \
                        and last["content"] and last["content"][0].get("type") == "tool_result":
                    last["content"].append(block)
                else:
                    messages.append({"role": "user", "content": [block]})
        return messages
