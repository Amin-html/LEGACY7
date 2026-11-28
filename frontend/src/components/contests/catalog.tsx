"use client";

import { useEffect, useState } from "react";

import { ContestCard, ContestCardSkeleton } from "@/components/contests/contest-card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import type { Category, ContestSummary, Page } from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

const PAGE_SIZE = 12;
const ORDERINGS = [
  { value: "-starts_at", label: "Сначала новые" },
  { value: "deadline", label: "Скоро дедлайн" },
  { value: "-prize_pool", label: "Больше призовой фонд" },
];

export function Catalog() {
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [category, setCategory] = useState("");
  const [onlyOpen, setOnlyOpen] = useState(false);
  const [ordering, setOrdering] = useState("-starts_at");
  const [page, setPage] = useState(1);

  // Поиск отправляем с задержкой, чтобы не стучаться на каждую букву
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebounced(search.trim());
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [search]);

  const params = new URLSearchParams();
  if (debounced) params.set("search", debounced);
  if (category) params.set("category", category);
  if (onlyOpen) params.set("open", "true");
  params.set("ordering", ordering);
  if (page > 1) params.set("page", String(page));

  const categories = useApiData<Category[]>("/categories/");
  const contests = useApiData<Page<ContestSummary>>(`/contests/?${params.toString()}`);

  const totalPages = contests.data ? Math.max(1, Math.ceil(contests.data.count / PAGE_SIZE)) : 1;
  const filtersActive = Boolean(debounced || category || onlyOpen);

  function change<T>(setter: (value: T) => void, value: T) {
    setter(value);
    setPage(1);
  }

  function reset() {
    setSearch("");
    setDebounced("");
    setCategory("");
    setOnlyOpen(false);
    setPage(1);
  }

  function goTo(next: number) {
    setPage(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="font-display text-3xl font-extrabold md:text-4xl">Конкурсы</h1>
      <p className="mt-2 text-muted">Выбери конкурс, покажи свою работу и поборись за призы.</p>

      <div className="mt-8 space-y-4">
        <div className="flex flex-col gap-3 md:flex-row">
          <div className="flex-1">
            <label htmlFor="search" className="sr-only">
              Поиск конкурсов
            </label>
            <input
              id="search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Поиск по названию и описанию"
              className="h-11 w-full rounded-xl border border-white/15 bg-graphite/80 px-4 placeholder:text-muted/70 focus:border-gold"
            />
          </div>
          <div>
            <label htmlFor="ordering" className="sr-only">
              Сортировка
            </label>
            <select
              id="ordering"
              value={ordering}
              onChange={(event) => change(setOrdering, event.target.value)}
              className="h-11 w-full rounded-xl border border-white/15 bg-graphite px-4 focus:border-gold md:w-60"
            >
              {ORDERINGS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Категории">
          <button
            type="button"
            aria-pressed={category === ""}
            onClick={() => change(setCategory, "")}
            className={chip(category === "")}
          >
            Все
          </button>
          {categories.data?.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={category === item.slug}
              onClick={() => change(setCategory, item.slug)}
              className={chip(category === item.slug)}
            >
              {item.name}
            </button>
          ))}
          <label className="ml-auto flex cursor-pointer items-center gap-2 text-sm text-muted">
            <input
              type="checkbox"
              checked={onlyOpen}
              onChange={(event) => change(setOnlyOpen, event.target.checked)}
              className="size-4 accent-gold"
            />
            Только с открытым приёмом
          </label>
        </div>
      </div>

      <p aria-live="polite" className="mt-6 text-sm text-muted">
        {contests.data ? `Найдено: ${contests.data.count}` : "\u00a0"}
      </p>

      <div className="mt-4">
        {contests.error ? (
          <div role="alert" className="rounded-2xl border border-danger/40 bg-danger/10 p-6 text-center">
            <p className="text-danger">Не удалось загрузить конкурсы.</p>
            <Button variant="secondary" size="sm" className="mt-4" onClick={contests.reload}>
              Попробовать снова
            </Button>
          </div>
        ) : contests.loading ? (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }, (_, index) => (
              <ContestCardSkeleton key={index} />
            ))}
          </div>
        ) : contests.data && contests.data.results.length > 0 ? (
          <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {contests.data.results.map((contest) => (
              <li key={contest.id}>
                <ContestCard contest={contest} />
              </li>
            ))}
          </ul>
        ) : (
          <div className="rounded-2xl border border-white/10 p-10 text-center">
            <p className="font-display text-lg font-bold">Ничего не найдено</p>
            <p className="mt-1 text-muted">Измени запрос или сбрось фильтры.</p>
            {filtersActive && (
              <Button variant="secondary" size="sm" className="mt-4" onClick={reset}>
                Сбросить фильтры
              </Button>
            )}
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <nav aria-label="Страницы" className="mt-10 flex items-center justify-center gap-4">
          <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => goTo(page - 1)}>
            Назад
          </Button>
          <span className="text-sm text-muted">
            Страница {page} из {totalPages}
          </span>
          <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => goTo(page + 1)}>
            Далее
          </Button>
        </nav>
      )}
    </main>
  );
}

function chip(active: boolean): string {
  return cn(
    "rounded-full border px-4 py-1.5 text-sm transition",
    active ? "border-gold bg-gold/15 text-gold" : "border-white/15 text-snow/80 hover:border-white/40",
  );
}