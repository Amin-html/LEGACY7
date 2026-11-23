"use client";

import Link from "next/link";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import type { LeaderRow, Page } from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

export function TopParticipants() {
  const { data, loading, error } = useApiData<Page<LeaderRow>>("/leaderboard/");
  const rows = data?.results.slice(0, 5) ?? [];

  return (
    <section aria-labelledby="top-title">
      <div className="mb-5 flex items-end justify-between gap-4">
        <h2 id="top-title" className="font-display text-2xl font-bold">
          Топ участников
        </h2>
        <Link href="/leaderboard" className="text-sm text-gold hover:underline">
          Весь рейтинг
        </Link>
      </div>

      <Card className="p-2">
        {loading ? (
          <div aria-hidden="true" className="space-y-2 p-3">
            {Array.from({ length: 5 }, (_, index) => (
              <div key={index} className="h-9 animate-pulse rounded bg-white/5" />
            ))}
          </div>
        ) : error ? (
          <p role="alert" className="p-4 text-danger">
            Не удалось загрузить рейтинг.
          </p>
        ) : rows.length === 0 ? (
          <p className="p-4 text-muted">Рейтинг появится после первых завершённых конкурсов.</p>
        ) : (
          <ol>
            {rows.map((row) => (
              <li key={row.user.id} className="flex items-center gap-3 rounded-xl px-3 py-2.5">
                <span
                  className={cn(
                    "grid size-7 shrink-0 place-items-center rounded-full text-sm font-bold",
                    row.place === 1 ? "bg-gold text-ink" : "bg-white/10 text-snow",
                  )}
                >
                  {row.place}
                </span>
                <span className="min-w-0 flex-1 truncate font-medium">{row.user.username}</span>
                <span className="text-sm font-semibold text-gold">{formatNumber(row.points)}</span>
              </li>
            ))}
          </ol>
        )}
      </Card>
    </section>
  );
}