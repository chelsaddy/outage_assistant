"use client";

import type { ConversationSummary } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { Badge } from "./Badge";

export function ConversationList({
  conversations,
  selectedId,
  onSelect,
}: {
  conversations: ConversationSummary[] | null;
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  if (conversations === null) return <p className="p-4 text-sm text-zinc-500">Loading…</p>;
  if (conversations.length === 0)
    return <p className="p-4 text-sm text-zinc-500">No conversations yet. Start one as a customer.</p>;

  return (
    <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
      {conversations.map((c) => (
        <li key={c.id}>
          <button
            onClick={() => onSelect(c.id)}
            className={`block w-full px-4 py-3 text-left hover:bg-zinc-100 dark:hover:bg-zinc-900 ${
              c.id === selectedId ? "bg-zinc-100 dark:bg-zinc-900" : ""
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="truncate text-sm font-medium">{c.customer_name ?? "Unidentified customer"}</span>
              <Badge value={c.status} className="ml-auto" />
            </div>
            <p className="mt-1 truncate text-sm text-zinc-500">{c.last_message ?? "…"}</p>
            <div className="mt-1 flex gap-3 text-xs text-zinc-400">
              <span>#{c.id}</span>
              <span>{c.tool_calls} tool calls</span>
              <span className="ml-auto">{timeAgo(c.last_activity)}</span>
            </div>
          </button>
        </li>
      ))}
    </ul>
  );
}
