"use client";

import { api } from "@/lib/api";
import { clock, timeAgo } from "@/lib/format";
import { usePoll } from "@/lib/usePoll";
import { Badge } from "@/components/Badge";

export default function SmsPage() {
  const sms = usePoll(() => api.sms(), [], 5000);

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-lg font-semibold">SMS outbox</h1>
        <p className="mt-1 mb-4 text-sm text-zinc-500">
          Every text the agent sends. Without Twilio keys, messages are recorded as{" "}
          <Badge value="simulated" /> instead of being delivered.
        </p>

        {sms.error && <p className="mb-3 text-sm text-rose-600">Could not load SMS: {sms.error}</p>}
        {sms.data === null && !sms.error && <p className="text-sm text-zinc-500">Loading…</p>}
        {sms.data?.length === 0 && <p className="text-sm text-zinc-500">No messages sent yet.</p>}

        <ul className="space-y-3">
          {sms.data?.map((m) => (
            <li
              key={m.id}
              className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950"
            >
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-medium">{m.customer_name ?? "Unknown"}</span>
                <span className="font-mono text-zinc-500">{m.to_phone}</span>
                <Badge value={m.status} className="ml-auto" />
              </div>
              <p className="mt-2 text-sm whitespace-pre-wrap">{m.body}</p>
              <div className="mt-2 flex gap-3 text-xs text-zinc-400">
                <span title={clock(m.created_at)}>{timeAgo(m.created_at)}</span>
                <span>{m.body.length} chars</span>
                {m.provider_sid && <span className="font-mono">{m.provider_sid}</span>}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
