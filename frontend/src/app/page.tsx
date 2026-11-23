import Link from "next/link";

import { PopularContests } from "@/components/home/popular-contests";
import { TopParticipants } from "@/components/home/top-participants";
import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const PERKS = [
  { title: "Участвуй", text: "В конкурсах и челленджах" },
  { title: "Развивайся", text: "Показывай свой талант" },
  { title: "Зарабатывай", text: "Получай баллы и награды" },
];

export default function HomePage() {
  return (
    <main>
      <section className="hero-bg">
        <div className="mx-auto max-w-6xl px-4 py-24 md:py-32">
          <p className="mb-4 text-xs font-semibold uppercase tracking-[0.3em] text-muted">
            Платформа онлайн-конкурсов
          </p>
          <h1 className="font-display text-5xl font-extrabold leading-tight md:text-7xl">
            LEGACY <span className="text-gold">7</span>
          </h1>
          <p className="mt-4 text-xl font-semibold">Твой талант. Твоя победа.</p>
          <p className="mt-3 max-w-xl text-muted">
            Участвуй в конкурсах, проявляй себя, получай признание и зарабатывай баллы. Стань частью
            LEGACY 7.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/contests" className={buttonStyles({ size: "lg" })}>
              Перейти к конкурсам
            </Link>
            <Link href="/about" className={buttonStyles({ variant: "secondary", size: "lg" })}>
              О проекте
            </Link>
          </div>
        </div>
      </section>

      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 lg:grid-cols-[1fr_340px]">
        <PopularContests />
        <TopParticipants />
      </div>

      <section className="mx-auto grid max-w-6xl gap-4 px-4 pb-16 md:grid-cols-3">
        {PERKS.map((perk) => (
          <Card key={perk.title} className="p-6">
            <h2 className="font-display text-lg font-bold text-gold">{perk.title}</h2>
            <p className="mt-1 text-muted">{perk.text}</p>
          </Card>
        ))}
      </section>
    </main>
  );
}