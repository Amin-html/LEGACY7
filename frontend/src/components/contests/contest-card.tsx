import Link from "next/link";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { contestStage, formatDate, formatMoney, type StageTone } from "@/lib/format";
import type { ContestSummary } from "@/lib/types";

export const TONES: Record<StageTone, string> = {
  open: "bg-gold/15 text-gold",
  soon: "bg-white/10 text-snow",
  closed: "bg-white/10 text-muted",
  info: "bg-info/15 text-info",
  done: "bg-white/10 text-muted",
};

export function ContestCard({ contest }: { contest: ContestSummary }) {
  const stage = contestStage(contest);
  return (
    <Link href={`/contests/${encodeURIComponent(contest.slug)}`} className="group block h-full rounded-2xl">
      <Card className="flex h-full flex-col overflow-hidden transition duration-200 group-hover:-translate-y-0.5 group-hover:border-gold/50">
        <div className="relative h-40 bg-linear-to-br from-navy to-graphite">
          {contest.cover && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={contest.cover}
              alt=""
              loading="lazy"
              className="size-full object-cover transition duration-300 group-hover:scale-105"
            />
          )}
          <span className="absolute left-3 top-3 rounded-full bg-ink/80 px-3 py-1 text-xs font-medium text-snow">
            {contest.category.name}
          </span>
        </div>
        <div className="flex flex-1 flex-col gap-3 p-4">
          <span className={cn("self-start rounded-full px-2.5 py-0.5 text-xs font-semibold", TONES[stage.tone])}>
            {stage.label}
          </span>
          <h3 className="font-display text-lg font-bold leading-snug">{contest.title}</h3>
          <dl className="mt-auto space-y-1 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Дедлайн</dt>
              <dd>{formatDate(contest.deadline)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Призовой фонд</dt>
              <dd className="font-semibold text-gold">{formatMoney(contest.prize_pool, contest.currency)}</dd>
            </div>
          </dl>
        </div>
      </Card>
    </Link>
  );
}

export function ContestCardSkeleton() {
  return (
    <Card className="animate-pulse overflow-hidden" aria-hidden="true">
      <div className="h-40 bg-white/5" />
      <div className="space-y-3 p-4">
        <div className="h-5 w-28 rounded-full bg-white/10" />
        <div className="h-6 w-3/4 rounded bg-white/10" />
        <div className="h-4 w-full rounded bg-white/5" />
        <div className="h-4 w-2/3 rounded bg-white/5" />
      </div>
    </Card>
  );
}