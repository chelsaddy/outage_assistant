import Link from "next/link";
import type { ConversationDetail } from "@/lib/api";
import { label, timeAgo } from "@/lib/format";
import { Badge } from "./Badge";

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3 py-1">
      <dt className="text-zinc-500">{k}</dt>
      <dd className="text-right">{v ?? "—"}</dd>
    </div>
  );
}

export function ConversationDetails({ c }: { c: ConversationDetail }) {
  const toolCalls = c.steps.filter((s) => s.kind === "tool_call").length;
  return (
    <div className="space-y-6 p-4 text-sm">
      <section>
        <h3 className="mb-2 text-xs font-semibold tracking-wide text-zinc-500 uppercase">Conversation</h3>
        <dl>
          <Row k="ID" v={`#${c.id}`} />
          <Row k="Status" v={<Badge value={c.status} />} />
          <Row k="Started" v={timeAgo(c.created_at)} />
          <Row k="Tool calls" v={toolCalls} />
        </dl>
      </section>

      <section>
        <h3 className="mb-2 text-xs font-semibold tracking-wide text-zinc-500 uppercase">Customer</h3>
        {c.customer_id == null ? (
          <p className="text-zinc-500">Not identified yet.</p>
        ) : (
          <dl>
            <Row k="Name" v={c.customer_name} />
            <Row k="Account" v={c.account_no} />
            <Row k="Phone" v={c.phone} />
            <Row k="Service" v={label(c.service_type)} />
            <Row k="Area" v={c.area_name} />
          </dl>
        )}
      </section>

      <section>
        <h3 className="mb-2 text-xs font-semibold tracking-wide text-zinc-500 uppercase">Tickets</h3>
        {c.tickets.length === 0 ? (
          <p className="text-zinc-500">None opened.</p>
        ) : (
          <ul className="space-y-2">
            {c.tickets.map((t) => (
              <li key={t.id} className="rounded-lg border border-zinc-200 p-2 dark:border-zinc-800">
                <div className="flex items-center gap-2">
                  <Link href="/tickets" className="font-medium hover:underline">
                    #{t.id}
                  </Link>
                  <span className="text-zinc-500">{label(t.category)}</span>
                  <Badge value={t.priority} className="ml-auto" />
                </div>
                <p className="mt-1 text-zinc-600 dark:text-zinc-400">{t.summary}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
