"""The agent loop: native tool calling with the Anthropic SDK, no framework.

One call to run_turn() handles one customer message:
  log the message -> ask the model -> run any tools it calls -> repeat until it replies.
"""
import os

import anthropic
import httpx

from app.agent.prompt import EFFORT, MAX_ITERATIONS, MAX_TOKENS, MODEL, SYSTEM_PROMPT
from app.agent.store import ConversationStore
from app.agent.tools import TOOL_DEFINITIONS, ToolExecutor
from app.helpers.auth import service_headers

TOOLS_API_URL = os.environ.get("TOOLS_API_URL", "http://localhost:8000")

ESCALATED_REPLY = ("Thanks for your patience. Your case is with a member of our care team, "
                   "and they will contact you shortly.")


def default_llm() -> anthropic.Anthropic:
    return anthropic.Anthropic()  # reads ANTHROPIC_API_KEY


def default_api() -> httpx.Client:
    return httpx.Client(base_url=TOOLS_API_URL, headers=service_headers(), timeout=15)


def _text_of(content: list) -> str:
    return "\n".join(b.text for b in content if b.type == "text").strip()


def _call_model(llm: anthropic.Anthropic, messages: list[dict]):
    return llm.beta.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        tools=TOOL_DEFINITIONS,
        messages=messages,
        output_config={"effort": EFFORT},
        cache_control={"type": "ephemeral"},        # system + tools + history are re-sent every loop
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",                          # if a safety classifier declines, retry on another model
    )


def run_turn(
    conversation_id: int | None,
    message: str,
    *,
    llm: anthropic.Anthropic | None = None,
    api: httpx.Client | None = None,
) -> dict:
    store = ConversationStore.open(conversation_id)
    first_step = store.last_step_no()
    store.log("user_message", {"text": message})

    # Escalated conversations belong to a person now: record the message, don't act on it.
    if store.status() == "escalated":
        return _finish(store, first_step, ESCALATED_REPLY, canned=True)

    llm = llm or default_llm()
    api = api or default_api()
    executor = ToolExecutor(api, store)

    for _ in range(MAX_ITERATIONS):
        response = _call_model(llm, store.history())

        if response.stop_reason == "refusal":
            executor.run("escalate_to_human", {"reason": "low_confidence",
                                               "summary": "The model declined to handle this message."})
            return _finish(store, first_step, ESCALATED_REPLY, canned=True)

        # Store the content blocks exactly as returned, so the next request replays them unchanged.
        store.log("assistant_message", {
            "content": [b.to_dict() for b in response.content],
            "text": _text_of(response.content),
            "stop_reason": response.stop_reason,
            "usage": {"input": response.usage.input_tokens, "output": response.usage.output_tokens},
        })

        if response.stop_reason == "tool_use":
            for block in (b for b in response.content if b.type == "tool_use"):
                store.log("tool_call", {"tool_use_id": block.id, "input": block.input}, tool_name=block.name)
                result = executor.run(block.name, block.input)
                store.log("tool_result", {"tool_use_id": block.id, "content": result.content,
                                          "is_error": result.is_error}, tool_name=block.name)
            continue

        if response.stop_reason == "pause_turn":
            continue

        if response.stop_reason == "max_tokens":
            executor.run("escalate_to_human", {"reason": "tool_failure",
                                               "summary": "The agent's response was cut off (max_tokens)."})
            return _finish(store, first_step, ESCALATED_REPLY, canned=True)

        return _finish(store, first_step, _text_of(response.content))  # end_turn

    executor.run("escalate_to_human", {"reason": "tool_failure",
                                       "summary": f"No answer after {MAX_ITERATIONS} model calls."})
    return _finish(store, first_step, ESCALATED_REPLY, canned=True)


def _finish(store: ConversationStore, first_step: int, reply: str, canned: bool = False) -> dict:
    if canned:  # a reply the model didn't write; log it so the trace shows what the customer saw
        store.log("assistant_message", {"content": [{"type": "text", "text": reply}], "text": reply,
                                        "canned": True})
    steps = store.steps(after_step=first_step)
    return {
        "conversation_id": store.conversation_id,
        "reply": reply,
        "status": store.status(),
        "tools_called": [s["tool_name"] for s in steps if s["kind"] == "tool_call"],
        "steps": steps,
    }
