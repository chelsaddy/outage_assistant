"use client";

import Link from "next/link";
import { useState } from "react";
import { api, type TicketStatus } from "@/lib/api";
import { label, timeAgo } from "@/lib/format";
import { usePoll } from "@/lib/usePoll";
import { Badge } from "@/components/Badge";

const TABS: { value: TicketStatus | undefined; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In progress" },
  { value: "closed", label: "Closed" },
  { value: undefined, label: "All" },
];

export default function TicketsPage() {
  const [status, setStatus] = useState<TicketStatus | undefined>("open");
  const [updateError, setUpdateError] = useState<string | null>(null);
  const tickets = usePoll(() => api.tickets(status), [status], 5000);

  const move = async (id: number, next: TicketStatus) => {
    setUpdateError(null);
    try {
      await api.updateTicket(id, next);
      await tickets.refresh();
    } catch (e) {
      setUpdateError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6">
      <div className="mx-auto max-w-6xl">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <h1 className="mr-4 text-lg font-semibold">Ticket queue</h1>
          {TABS.map((t) => (
            <button
              key={t.label}
              onClick={() => setStatus(t.value)}
              className={`rounded-md px-3 py-1 text-sm ${
                status === t.value
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-900"
              }`}
            >
              {t.label}
            </button>
          ))}
          <span className="ml-auto text-sm text-zinc-500">High priority first, then oldest</span>
        </div>

        {tickets.error && <p className="mb-3 text-sm text-rose-600">Could not load tickets: {tickets.error}</p>}
        {updateError && <p className="mb-3 text-sm text-rose-600">Update failed: {updateError}</p>}

        <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-zinc-200 text-xs text-zinc-500 uppercase dark:border-zinc-800">
              <tr>
                <th className="px-3 py-2 font-medium">Ticket</th>
                <th className="px-3 py-2 font-medium">Priority</th>
                <th className="px-3 py-2 font-medium">Customer</th>
                <th className="px-3 py-2 font-medium">Summary</th>
                <th className="px-3 py-2 font-medium">Opened</th>
                <th className="px-3 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
              {tickets.data?.map((t) => (
                <tr key={t.id} className="align-top">
                  <td className="px-3 py-3 whitespace-nowrap">
                    <div className="font-medium">#{t.id}</div>
                    <div className="text-zinc-500">{label(t.category)}</div>
                  </td>
                  <td className="px-3 py-3">
                    <Badge value={t.priority} />
                  </td>
                  <td className="px-3 py-3 whitespace-nowrap">
                    <div>{t.customer_name}</div>
                    <div className="text-zinc-500">
                      {label(t.service_type)} · {t.area_name}
                    </div>
                  </td>
                  <td className="max-w-md px-3 py-3">
                    <p>{t.summary}</p>
                    {t.conversation_id != null && (
                      <Link href={`/?c=${t.conversation_id}`} className="text-xs text-sky-700 hover:underline dark:text-sky-400">
                        View conversation #{t.conversation_id}
                      </Link>
                    )}
                  </td>
                  <td className="px-3 py-3 whitespace-nowrap text-zinc-500">{timeAgo(t.created_at)}</td>
                  <td className="px-3 py-3">
                    <select
                      value={t.status}
                      onChange={(e) => move(t.id, e.target.value as TicketStatus)}
                      className="rounded-md border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-700"
                      aria-label={`Status of ticket ${t.id}`}
                    >
                      <option value="open">Open</option>
                      <option value="in_progress">In progress</option>
                      <option value="closed">Closed</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {tickets.data?.length === 0 && <p className="p-6 text-center text-sm text-zinc-500">No tickets here.</p>}
          {tickets.data === null && !tickets.error && <p className="p-6 text-center text-sm text-zinc-500">Loading…</p>}
        </div>
      </div>
    </div>
  );
}
