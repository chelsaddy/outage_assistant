"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Conversations" },
  { href: "/tickets", label: "Ticket queue" },
  { href: "/sms", label: "SMS outbox" },
];

const signOut = async () => {
  await fetch("/auth/logout", { method: "POST" }).catch(() => {});
  window.location.assign("/login");
};

export function Nav() {
  const path = usePathname();
  if (path === "/login") return null;
  return (
    <header className="border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex h-14 items-center gap-6 px-4">
        <span className="font-semibold tracking-tight">Outage Assistant</span>
        <nav className="flex gap-1 text-sm">
          {LINKS.map((l) => {
            const active = l.href === "/" ? path === "/" : path.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded-md px-3 py-1.5 ${
                  active
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                    : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-900"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
        <button
          onClick={signOut}
          className="ml-auto rounded-md px-3 py-1.5 text-sm text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-900"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
