"use client";

import { useState } from "react";
import type { AgentStep } from "@/lib/api";
import { clock, label, prettyJson } from "@/lib/format";

type Item =
  | { type: "user"; key: string; text: string; at: string }
  | { type: "agent"; key: string; text: string; at: string; canned: boolean }
  | { type: "tool"; key: string; name: string; input: unknown; result?: { content: unknown; isError: boolean }; at: string }
  | { type: "escalation"; key: string; reason: string; summary: string; ticketId: number | null; at: string };

/** Turn the raw step log into what a person reads: messages, tool calls paired with results, escalations. */
function toItems(steps: AgentStep[]): Item[] {
  const items: Item[] = [];
  const tools = new Map<string, Extract<Item, { type: "tool" }>>();

  for (const s of steps) {
    const p = s.payload as Record<string, unknown>;
    const key = String(s.step_no);
    switch (s.kind) {
      case "user_message":
        items.push({ type: "user", key, text: String(p.text ?? ""), at: s.created_at });
        break;
      case "assistant_message": {
        const text = String(p.text ?? "").trim();
        if (text) items.push({ type: "agent", key, text, at: s.created_at, canned: Boolean(p.canned) });
        break;
      }
      case "tool_call": {
        const item = { type: "tool" as const, key, name: s.tool_name ?? "tool", input: p.input, at: s.created_at };
        tools.set(String(p.tool_use_id), item);
        items.push(item);
        break;
      }
      case "tool_result": {
        const call = tools.get(String(p.tool_use_id));
        if (call) call.result = { content: p.content, isError: Boolean(p.is_error) };
        break;
      }
      case "escalation":
        items.push({
          type: "escalation",
          key,
          reason: String(p.reason ?? ""),
          summary: String(p.summary ?? ""),
          ticketId: (p.ticket_id as number | null) ?? null,
          at: s.created_at,
        });
        break;
    }
  }
  return items;
}

function ToolCard({ item }: { item: Extract<Item, { type: "tool" }> }) {
  const [open, setOpen] = useState(false);
  const status = !item.result ? "running" : item.result.isError ? "error" : "ok";
  const dot = { running: "bg-amber-400 animate-pulse", error: "bg-rose-500", ok: "bg-emerald-500" }[status];

  return (
    <div className="mx-auto w-full max-w-xl rounded-lg border border-zinc-200 bg-white text-xs dark:border-zinc-800 dark:bg-zinc-900">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
        aria-expanded={open}
      >
        <span className={`h-2 w-2 shrink-0 rounded-full ${dot}`} />
        <span className="font-mono font-medium">{item.name}</span>
        <span className="truncate font-mono text-zinc-500">{JSON.stringify(item.input)}</span>
        <span className="ml-auto shrink-0 text-zinc-400">{open ? "hide" : "show"}</span>
      </button>
      {open && (
        <div className="space-y-2 border-t border-zinc-200 px-3 py-2 dark:border-zinc-800">
          <Block title="Input" body={prettyJson(item.input)} />
          {item.result && (
            <Block title={item.result.isError ? "Error" : "Result"} body={prettyJson(item.result.content)} error={item.result.isError} />
          )}
        </div>
      )}
    </div>
  );
}

function Block({ title, body, error = false }: { title: string; body: string; error?: boolean }) {
  return (
    <div>
      <div className={`mb-1 font-medium ${error ? "text-rose-600 dark:text-rose-400" : "text-zinc-500"}`}>{title}</div>
      <pre className="max-h-64 overflow-auto rounded bg-zinc-50 p-2 font-mono whitespace-pre-wrap break-words dark:bg-zinc-950">
        {body}
      </pre>
    </div>
  );
}

export function Transcript({
  steps,
  showTrace,
  pending,
}: {
  steps: AgentStep[];
  showTrace: boolean;
  pending: string | null;
}) {
  const items = toItems(steps).filter((i) => showTrace || i.type !== "tool");

  return (
    <div className="flex flex-col gap-3">
      {items.map((item) => {
        switch (item.type) {
          case "user":
            return (
              <div key={item.key} className="flex flex-col items-start">
                <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-white px-4 py-2 whitespace-pre-wrap shadow-sm ring-1 ring-zinc-200 dark:bg-zinc-900 dark:ring-zinc-800">
                  {item.text}
                </div>
                <span className="mt-1 text-xs text-zinc-400">Customer · {clock(item.at)}</span>
              </div>
            );
          case "agent":
            return (
              <div key={item.key} className="flex flex-col items-end">
                <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-zinc-900 px-4 py-2 whitespace-pre-wrap text-white dark:bg-zinc-100 dark:text-zinc-900">
                  {item.text}
                </div>
                <span className="mt-1 text-xs text-zinc-400">
                  Agent{item.canned ? " (standard reply)" : ""} · {clock(item.at)}
                </span>
              </div>
            );
          case "tool":
            return <ToolCard key={item.key} item={item} />;
          case "escalation":
            return (
              <div
                key={item.key}
                className="mx-auto w-full max-w-xl rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm dark:border-rose-900 dark:bg-rose-950/50"
              >
                <div className="font-medium text-rose-800 dark:text-rose-300">
                  Escalated to a human: {label(item.reason)}
                  {item.ticketId != null && <span className="font-normal"> · ticket #{item.ticketId}</span>}
                </div>
                <p className="mt-1 text-rose-900/80 dark:text-rose-200/80">{item.summary}</p>
              </div>
            );
        }
      })}

      {pending && (
        <>
          <div className="flex flex-col items-start opacity-70">
            <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-white px-4 py-2 whitespace-pre-wrap shadow-sm ring-1 ring-zinc-200 dark:bg-zinc-900 dark:ring-zinc-800">
              {pending}
            </div>
          </div>
          <div className="self-end text-sm text-zinc-500 animate-pulse">Agent is working…</div>
        </>
      )}
    </div>
  );
}
