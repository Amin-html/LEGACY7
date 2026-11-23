import type { Metadata } from "next";
import Link from "next/link";

import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export const metadata: Metadata = { title: "О платформе" };

const STEPS = [
  { title: "Выбери конкурс", text: "Фотография, дизайн, код, видео и спорт: у каждого свои правила и призы." },
  { title: "Подай работу", text: "Опиши идею, приложи файл или ссылку. До дедлайна работу можно править." },
  { title: "Получи оценку", text: "Независимое жюри оценивает по критериям, не зная автора работы." },
  { title: "Расти в рейтинге", text: "Очки за каждый конкурс складываются в общий рейтинг участников." },
];

export default function AboutPage() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="font-display text-3xl font-extrabold md:text-5xl">
        LEGACY <span className="text-gold">7</span>
      </h1>
      <p className="mt-4 max-w-2xl text-lg text-snow/85">
        Платформа онлайн-конкурсов, где талант получает признание. Организаторы создают конкурсы,
        участники подают работы, жюри оценивает, а система честно считает рейтинг.
      </p>

      <ol className="mt-10 grid gap-4 sm:grid-cols-2">
        {STEPS.map((step, index) => (
          <li key={step.title}>
            <Card className="h-full p-5">
              <span className="font-display text-sm font-bold text-gold">0{index + 1}</span>
              <h2 className="mt-1 font-display text-lg font-bold">{step.title}</h2>
              <p className="mt-1 text-muted">{step.text}</p>
            </Card>
          </li>
        ))}
      </ol>

      <div className="mt-10 flex flex-wrap gap-3">
        <Link href="/contests" className={buttonStyles({ size: "lg" })}>
          К конкурсам
        </Link>
        <Link href="/register" className={buttonStyles({ variant: "secondary", size: "lg" })}>
          Создать аккаунт
        </Link>
      </div>
    </main>
  );
}