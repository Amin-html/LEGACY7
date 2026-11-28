"use client";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { formatMoney, formatNumber } from "@/lib/format";
import type { ContestResultsData } from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

export function ContestResults({ slug, currency }: { slug: string; currency: string }) {
  const { data, loading, error } = useApiData<ContestResultsData>(
    `/contests/${encodeURIComponent(slug)}/results/`,
  );
  const rows = data?.results ?? [];
  const showTitles = rows.some((row) => row.title);

  return (
    <section aria-labelledby="results-title" className="mt-12">
      <h2 id="results-title" className="font-display text-2xl font-bold">
        Итоги конкурса
      </h2>
      <Card className="mt-4 overflow-x-auto">
        {loading ? (
          <div aria-hidden="true" className="space-y-2 p-4">
            {Array.from({ length: 3 }, (_, index) => (
              <div key={index} className="h-9 animate-pulse rounded bg-white/5" />
            ))}
          </div>
        ) : error ? (
          <p role="alert" className="p-4 text-danger">
            Не удалось загрузить итоги.
          </p>
        ) : rows.length === 0 ? (
          <p className="p-4 text-muted">Итоги пока не опубликованы.</p>
        ) : (
          <table className="w-full min-w-[32rem] text-left text-sm">
            <caption className="sr-only">Итоги конкурса</caption>
            <thead className="border-b border-white/10 text-muted">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">Место</th>
                <th scope="col" className="px-4 py-3 font-medium">Участник</th>
                {showTitles && <th scope="col" className="px-4 py-3 font-medium">Работа</th>}
                <th scope="col" className="px-4 py-3 text-right font-medium">Балл</th>
                <th scope="col" className="px-4 py-3 text-right font-medium">Приз</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.place}-${row.username}`} className="border-b border-white/5 last:border-0">
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "grid size-7 place-items-center rounded-full font-bold",
                        row.place === 1 ? "bg-gold text-ink" : "bg-white/10",
                      )}
                    >
                      {row.place}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-medium">{row.username}</td>
                  {showTitles && <td className="px-4 py-3 text-muted">{row.title}</td>}
                  <td className="px-4 py-3 text-right">
                    {row.score}
                    <span className="ml-1 text-xs text-muted">({formatNumber(row.points)})</span>
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-gold">
                    {row.prize ? formatMoney(row.prize, currency) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </section>
  );
}