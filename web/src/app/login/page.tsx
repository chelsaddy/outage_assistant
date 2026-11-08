"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";

// Only follow same-site paths after login, never another origin.
const safeNext = (next: string | null) => (next && next.startsWith("/") && !next.startsWith("//") ? next : "/");

function LoginForm() {
  const params = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (res.ok) {
        window.location.assign(safeNext(params.get("next")));
        return;
      }
      const body = await res.json().catch(() => ({}));
      setError(typeof body.detail === "string" ? body.detail : `Sign-in failed (HTTP ${res.status}).`);
    } catch {
      setError("Could not reach the dashboard server.");
    }
    setBusy(false);
  };

  const field =
    "w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-500 dark:border-zinc-700 dark:bg-zinc-900";

  return (
    <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Outage Assistant</h1>
        <p className="text-sm text-zinc-500">Sign in to the care team dashboard.</p>
      </div>
      <label className="block space-y-1 text-sm">
        <span>Username</span>
        <input className={field} value={username} onChange={(e) => setUsername(e.target.value)}
               autoComplete="username" autoFocus required />
      </label>
      <label className="block space-y-1 text-sm">
        <span>Password</span>
        <input className={field} type="password" value={password} onChange={(e) => setPassword(e.target.value)}
               autoComplete="current-password" required />
      </label>
      {error && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <button type="submit" disabled={busy}
              className="w-full rounded-lg bg-zinc-900 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900">
        {busy ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="flex h-full items-center justify-center px-4">
      <Suspense>
        <LoginForm />
      </Suspense>
    </div>
  );
}
