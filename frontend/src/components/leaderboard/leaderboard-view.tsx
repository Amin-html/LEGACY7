"use client";

import { useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import type { Category, LeaderRow, Page } from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

const PAGE_SIZE = 20;

export function LeaderboardView() {
  const { user } = useAuth();
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);

  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (page > 1) params.set("page", String(page));
  const query = params.toString();

  const categories = useApiData<Category[]>("/categories/");
  const board = useApiData<Page<LeaderRow>>(`/leaderboard/${query ? `?${query}` : ""}`);

  const totalPages = board.data ? Math.max(1, Math.ceil(board.data.count / PAGE_SIZE)) : 1;
  const rows = board.data?.results ?? [];

  function pick(slug: string) {
    setCategory(slug);
    setPage(1);
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="font-display text-3xl font-extrabold md:text-4xl">Рейтинг участников</h1>
      <p className="mt-2 text-muted">
        Очки начисляются за принятые работы в завершённых конкурсах: балл жюри × 100.
      </p>

      <div className="mt-6 flex flex-wrap gap-2" role="group" aria-label="Категории">
        <Chip active={category === ""} onClick={() => pick("")}>
          Общий
        </Chip>
        {categories.data?.map((item) => (
          <Chip key={item.id} active={category === item.slug} onClick={() => pick(item.slug)}>
            {item.name}
          </Chip>
        ))}
      </div>

      <Card className="mt-6 overflow-x-auto">
        {board.loading ? (
          <div aria-hidden="true" className="space-y-2 p-4">
            {Array.from({ length: 6 }, (_, index) => (
              <div key={index} className="h-10 animate-pulse rounded bg-white/5" />
            ))}
          </div>
        ) : board.error ? (
          <div role="alert" className="p-6 text-center">
            <p className="text-danger">Не удалось загрузить рейтинг.</p>
            <Button variant="secondary" size="sm" className="mt-4" onClick={board.reload}>
              Попробовать снова
            </Button>
          </div>
        ) : rows.length === 0 ? (
          <p className="p-8 text-center text-muted">
            Здесь пока пусто. Рейтинг появится после первых завершённых конкурсов.
          </p>
        ) : (
          <table className="w-full min-w-[28rem] text-left text-sm">
            <caption className="sr-only">Рейтинг участников</caption>
            <thead className="border-b border-white/10 text-muted">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">Место</th>
                <th scope="col" className="px-4 py-3 font-medium">Участник</th>
                <th scope="col" className="px-4 py-3 text-right font-medium">Конкурсов</th>
                <th scope="col" className="px-4 py-3 text-right font-medium">Очки</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.user.id}
                  className={cn(
                    "border-b border-white/5 last:border-0",
                    user?.id === row.user.id && "bg-gold/10",
                  )}
                >
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
                  <td className="px-4 py-3 font-medium">
                    {row.user.username}
                    {user?.id === row.user.id && <span className="ml-2 text-xs text-gold">это ты</span>}
                  </td>
                  <td className="px-4 py-3 text-right text-muted">{row.contests}</td>
                  <td className="px-4 py-3 text-right font-semibold text-gold">
                    {formatNumber(row.points)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {totalPages > 1 && (
        <nav aria-label="Страницы" className="mt-8 flex items-center justify-center gap-4">
          <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Назад
          </Button>
          <span className="text-sm text-muted">
            Страница {page} из {totalPages}
          </span>
          <Button
            variant="secondary"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            Далее
          </Button>
        </nav>
      )}
    </main>
  );
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "rounded-full border px-4 py-1.5 text-sm transition",
        active ? "border-gold bg-gold/15 text-gold" : "border-white/15 text-snow/80 hover:border-white/40",
      )}
    >
      {children}
    </button>
  );
}