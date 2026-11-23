"use client";

import Link from "next/link";

import { ContestCard, ContestCardSkeleton } from "@/components/contests/contest-card";
import type { ContestSummary, Page } from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

export function PopularContests() {
  const { data, loading, error } = useApiData<Page<ContestSummary>>(
    "/contests/?open=true&ordering=-prize_pool",
  );
  const items = data?.results.slice(0, 4) ?? [];

  return (
    <section aria-labelledby="popular-title">
      <div className="mb-5 flex items-end justify-between gap-4">
        <h2 id="popular-title" className="font-display text-2xl font-bold">
          Популярные конкурсы
        </h2>
        <Link href="/contests" className="text-sm text-gold hover:underline">
          Все конкурсы
        </Link>
      </div>

      {loading ? (
        <div className="grid gap-5 sm:grid-cols-2">
          {Array.from({ length: 2 }, (_, index) => (
            <ContestCardSkeleton key={index} />
          ))}
        </div>
      ) : error ? (
        <p role="alert" className="text-danger">
          Не удалось загрузить конкурсы.
        </p>
      ) : items.length === 0 ? (
        <p className="text-muted">Сейчас нет конкурсов с открытым приёмом. Загляни в каталог.</p>
      ) : (
        <ul className="grid gap-5 sm:grid-cols-2">
          {items.map((contest) => (
            <li key={contest.id}>
              <ContestCard contest={contest} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}