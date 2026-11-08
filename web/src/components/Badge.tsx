import { label } from "@/lib/format";

const TONES: Record<string, string> = {
  // conversation status
  open: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300",
  escalated: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300",
  closed: "bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  // ticket status / priority
  in_progress: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  high: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300",
  normal: "bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  low: "bg-zinc-100 text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400",
  // sms status
  sent: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  simulated: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300",
  failed: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300",
};

export function Badge({ value, className = "" }: { value: string; className?: string }) {
  const tone = TONES[value] ?? "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${tone} ${className}`}>
      {label(value)}
    </span>
  );
}
