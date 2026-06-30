import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: boolean;
}

export function StatCard({ label, value, sub, accent }: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border p-5",
        accent
          ? "bg-indigo-600 border-indigo-600 text-white"
          : "bg-white border-slate-100 shadow-sm"
      )}
    >
      <p
        className={cn(
          "text-xs font-semibold uppercase tracking-wide mb-2",
          accent ? "text-indigo-200" : "text-slate-400"
        )}
      >
        {label}
      </p>
      <p
        className={cn(
          "font-outfit text-3xl font-bold",
          accent ? "text-white" : "text-slate-800"
        )}
      >
        {value}
      </p>
      {sub && (
        <p
          className={cn(
            "text-xs mt-1",
            accent ? "text-indigo-200" : "text-slate-400"
          )}
        >
          {sub}
        </p>
      )}
    </div>
  );
}
