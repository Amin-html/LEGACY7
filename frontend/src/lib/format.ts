const dateFormat = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short", year: "numeric" });
const numberFormat = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });

export function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso));
}

const dateTimeFormat = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso));
}

export function formatMoney(amount: string, currency: string): string {
  const unit = currency === "KGS" ? "сом" : currency;
  return `${numberFormat.format(Number(amount))} ${unit}`;
}

export function formatNumber(value: number): string {
  return numberFormat.format(value);
}

export type StageTone = "open" | "soon" | "closed" | "info" | "done";
export type Stage = { label: string; tone: StageTone };

/** Человеческий статус конкурса. Date.now() держим здесь, а не в компонентах. */
export function contestStage(contest: { status: string; is_open: boolean; starts_at: string }): Stage {
  if (contest.status === "finished") return { label: "Завершён", tone: "done" };
  if (contest.status === "judging") return { label: "Идёт оценивание", tone: "info" };
  if (contest.is_open) return { label: "Идёт приём работ", tone: "open" };
  if (new Date(contest.starts_at).getTime() > Date.now()) return { label: "Скоро старт", tone: "soon" };
  return { label: "Приём закрыт", tone: "closed" };
}