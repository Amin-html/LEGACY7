"use client";

import Link from "next/link";

import { useAuth } from "@/components/auth/auth-provider";
import { TONES } from "@/components/contests/contest-card";
import { ContestResults } from "@/components/contests/contest-results";
import { Button, buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { contestStage, formatDateTime, formatMoney } from "@/lib/format";
import type { ContestDetail } from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

export function ContestView({ slug }: { slug: string }) {
  const { data: contest, loading, error, status, reload } = useApiData<ContestDetail>(
    `/contests/${encodeURIComponent(slug)}/`,
  );

  if (loading) return <ContestSkeleton />;

  if (status === 404) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-24 text-center">
        <h1 className="font-display text-3xl font-bold">Конкурс не найден</h1>
        <p className="mt-2 text-muted">Возможно, он ещё не опубликован или был перенесён в архив.</p>
        <Link href="/contests" className={buttonStyles({ className: "mt-6" })}>
          К списку конкурсов
        </Link>
      </main>
    );
  }

  if (error || !contest) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-24 text-center">
        <p role="alert" className="text-danger">
          Не удалось загрузить конкурс.
        </p>
        <Button variant="secondary" className="mt-4" onClick={reload}>
          Попробовать снова
        </Button>
      </main>
    );
  }

  const stage = contestStage(contest);

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <Link href="/contests" className="text-sm text-muted hover:text-gold">
        ← Все конкурсы
      </Link>

      <header className="mt-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-medium">
            {contest.category.name}
          </span>
          <span className={cn("rounded-full px-3 py-1 text-xs font-semibold", TONES[stage.tone])}>
            {stage.label}
          </span>
        </div>
        <h1 className="mt-3 font-display text-3xl font-extrabold md:text-5xl">{contest.title}</h1>
        <p className="mt-2 text-sm text-muted">Организатор: {contest.organizer}</p>
      </header>

      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_360px]">
        <div className="space-y-8">
          <dl className="grid gap-4 sm:grid-cols-3">
            <Fact label="Старт" value={formatDateTime(contest.starts_at)} />
            <Fact label="Дедлайн" value={formatDateTime(contest.deadline)} />
            <Fact
              label="Призовой фонд"
              value={formatMoney(contest.prize_pool, contest.currency)}
              accent
            />
          </dl>

          <section aria-labelledby="about-title">
            <h2 id="about-title" className="font-display text-xl font-bold">
              О конкурсе
            </h2>
            <p className="mt-2 whitespace-pre-line text-snow/85">{contest.description}</p>
          </section>

          {contest.rules && (
            <section aria-labelledby="rules-title">
              <h2 id="rules-title" className="font-display text-xl font-bold">
                Правила
              </h2>
              <p className="mt-2 whitespace-pre-line text-snow/85">{contest.rules}</p>
            </section>
          )}

          {contest.criteria.length > 0 && (
            <section aria-labelledby="criteria-title">
              <h2 id="criteria-title" className="font-display text-xl font-bold">
                Как оценивают
              </h2>
              <ul className="mt-3 grid gap-3 sm:grid-cols-2">
                {contest.criteria.map((criterion) => (
                  <li key={criterion.id}>
                    <Card className="p-4">
                      <p className="font-semibold">{criterion.title}</p>
                      <p className="mt-1 text-sm text-muted">
                        До {criterion.max_score} баллов, вес ×{Number(criterion.weight)}
                      </p>
                    </Card>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>

        <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
          <Card className="p-5">
            <h2 className="font-display text-lg font-bold">Призы</h2>
            {contest.prizes.length === 0 ? (
              <p className="mt-2 text-sm text-muted">Призы будут объявлены позже.</p>
            ) : (
              <ol className="mt-3 space-y-2">
                {contest.prizes.map((prize) => (
                  <li key={prize.place} className="flex items-center gap-3">
                    <span
                      className={cn(
                        "grid size-7 shrink-0 place-items-center rounded-full text-sm font-bold",
                        prize.place === 1 ? "bg-gold text-ink" : "bg-white/10",
                      )}
                    >
                      {prize.place}
                    </span>
                    <span className="flex-1 text-sm text-muted">{prize.description || "место"}</span>
                    <span className="font-semibold text-gold">
                      {formatMoney(prize.amount, contest.currency)}
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </Card>

          <Card className="p-5">
            <Participate contest={contest} stageLabel={stage.label} />
          </Card>
        </aside>
      </div>

      {contest.status === "finished" && (
        <ContestResults slug={contest.slug} currency={contest.currency} />
      )}
    </main>
  );
}

function Fact({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-graphite/60 p-4">
      <dt className="text-xs uppercase tracking-widest text-muted">{label}</dt>
      <dd className={cn("mt-1 font-semibold", accent && "text-gold")}>{value}</dd>
    </div>
  );
}

function Participate({ contest, stageLabel }: { contest: ContestDetail; stageLabel: string }) {
  const { user, status } = useAuth();

  if (!contest.is_open) {
    return <p className="text-center text-sm text-muted">{stageLabel}. Приём работ не идёт.</p>;
  }
  if (status === "loading") return <div aria-hidden="true" className="h-12" />;

  if (!user) {
    return (
      <div className="space-y-3 text-center">
        <Link href="/login" className={buttonStyles({ size: "lg", className: "w-full" })}>
          Войти и участвовать
        </Link>
        <p className="text-sm text-muted">
          Нет аккаунта?{" "}
          <Link href="/register" className="text-gold hover:underline">
            Зарегистрируйся
          </Link>
        </p>
      </div>
    );
  }

  if (user.role === "participant" || user.role === "admin") {
    return (
      <Link
        href={`/contests/${encodeURIComponent(contest.slug)}/submit`}
        className={buttonStyles({ size: "lg", className: "w-full" })}
      >
        Подать работу
      </Link>
    );
  }
  return (
    <p className="text-center text-sm text-muted">
      Подавать работы могут участники. Ты вошёл как организатор или судья.
    </p>
  );
}

function ContestSkeleton() {
  return (
    <main className="mx-auto max-w-6xl animate-pulse px-4 py-10" aria-busy="true">
      <div className="h-4 w-32 rounded bg-white/10" />
      <div className="mt-6 h-6 w-48 rounded-full bg-white/10" />
      <div className="mt-4 h-12 w-3/4 rounded bg-white/10" />
      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <div className="h-24 rounded-2xl bg-white/5" />
          <div className="h-40 rounded-2xl bg-white/5" />
        </div>
        <div className="h-64 rounded-2xl bg-white/5" />
      </div>
    </main>
  );
}