"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";
import { Badge } from "@/components/Badge";
import { Composer } from "@/components/Composer";
import { ConversationDetails } from "@/components/ConversationDetails";
import { ConversationList } from "@/components/ConversationList";
import { Transcript } from "@/components/Transcript";

type Filter = "open" | "escalated" | undefined;

function ConversationsView() {
  const router = useRouter();
  const params = useSearchParams();
  const selectedId = params.get("c") ? Number(params.get("c")) : null;
  const select = (id: number | null) => router.replace(id == null ? "/" : `/?c=${id}`, { scroll: false });

  const [filter, setFilter] = useState<Filter>(undefined);
  const [showTrace, setShowTrace] = useState(true);
  const [pending, setPending] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);

  const list = usePoll(() => api.conversations(filter), [filter]);
  const detail = usePoll(selectedId == null ? null : () => api.conversation(selectedId), [selectedId]);

  // Keep the newest message in view.
  const bottom = useRef<HTMLDivElement>(null);
  const stepCount = detail.data?.steps.length ?? 0;
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [stepCount, pending]);

  const send = async (text: string) => {
    setPending(text);
    setSendError(null);
    try {
      const res = await api.chat(text, selectedId);
      if (res.conversation_id !== selectedId) select(res.conversation_id);
      await Promise.all([detail.refresh(), list.refresh()]);
    } catch (e) {
      setSendError(e instanceof Error ? e.message : String(e));
    } finally {
      setPending(null);
    }
  };

  const c = detail.data;

  return (
    <div className="flex h-full">
      {/* Conversation list */}
      <aside
        className={`w-full shrink-0 flex-col border-r border-zinc-200 bg-white md:flex md:w-80 dark:border-zinc-800 dark:bg-zinc-950 ${
          selectedId != null || pending ? "hidden" : "flex"
        }`}
      >
        <div className="flex items-center gap-2 border-b border-zinc-200 p-3 dark:border-zinc-800">
          <select
            value={filter ?? ""}
            onChange={(e) => setFilter((e.target.value || undefined) as Filter)}
            className="rounded-md border border-zinc-300 bg-transparent px-2 py-1 text-sm dark:border-zinc-700"
            aria-label="Filter by status"
          >
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="escalated">Escalated</option>
          </select>
          <button
            onClick={() => select(null)}
            className="ml-auto rounded-md bg-zinc-900 px-3 py-1 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
          >
            New conversation
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {list.error && <p className="p-4 text-sm text-rose-600">Could not load conversations: {list.error}</p>}
          <ConversationList conversations={list.data} selectedId={selectedId} onSelect={select} />
        </div>
      </aside>

      {/* Transcript and composer */}
      <section className={`min-w-0 flex-1 flex-col ${selectedId != null || pending ? "flex" : "hidden md:flex"}`}>
        <div className="flex h-12 items-center gap-3 border-b border-zinc-200 px-4 dark:border-zinc-800">
          <button onClick={() => select(null)} className="text-sm text-zinc-500 md:hidden">
            ← Back
          </button>
          <h2 className="truncate text-sm font-medium">
            {selectedId == null ? "New conversation" : (c?.customer_name ?? `Conversation #${selectedId}`)}
          </h2>
          {c && <Badge value={c.status} />}
          <label className="ml-auto flex items-center gap-2 text-sm text-zinc-500">
            <input type="checkbox" checked={showTrace} onChange={(e) => setShowTrace(e.target.checked)} />
            Tool trace
          </label>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6">
          {detail.error && <p className="text-sm text-rose-600">Could not load conversation: {detail.error}</p>}
          {selectedId == null && !pending && (
            <p className="mx-auto max-w-md text-center text-sm text-zinc-500">
              Type a message as a customer to start a conversation with the agent. Seeded customers use phone
              numbers like 868-555-1000.
            </p>
          )}
          <Transcript steps={c?.steps ?? []} showTrace={showTrace} pending={pending} />
          <div ref={bottom} />
        </div>

        <div className="border-t border-zinc-200 p-3 dark:border-zinc-800">
          {sendError && <p className="mb-2 text-sm text-rose-600">Message not sent: {sendError}</p>}
          <Composer onSend={send} busy={pending !== null} />
        </div>
      </section>

      {/* Details */}
      <aside className="hidden w-72 shrink-0 overflow-y-auto border-l border-zinc-200 bg-white lg:block dark:border-zinc-800 dark:bg-zinc-950">
        {c ? <ConversationDetails c={c} /> : <p className="p-4 text-sm text-zinc-500">No conversation selected.</p>}
      </aside>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense>
      <ConversationsView />
    </Suspense>
  );
}
