"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { AccountActions } from "@/components/auth/account-actions";
import { Logo } from "@/components/logo";

import { cn } from "@/lib/cn";

const NAV = [
  { href: "/", label: "Главная" },
  { href: "/contests", label: "Конкурсы" },
  { href: "/leaderboard", label: "Рейтинг" },
  { href: "/about", label: "О платформе" },
];

export function Header() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
  const close = () => setOpen(false);

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-ink/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <Link href="/" aria-label="LEGACY 7, на главную" onClick={close}>
          <Logo />
        </Link>

        <nav aria-label="Основная навигация" className="hidden items-center gap-8 md:flex">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive(item.href) ? "page" : undefined}
              className={cn(
                "text-sm font-medium transition",
                isActive(item.href) ? "text-gold" : "text-snow/80 hover:text-snow",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="hidden md:block">
          <AccountActions layout="desktop" />
        </div>

        <button
          type="button"
          className="inline-flex size-10 items-center justify-center rounded-lg border border-white/15 md:hidden"
          aria-expanded={open}
          aria-controls="mobile-menu"
          aria-label={open ? "Закрыть меню" : "Открыть меню"}
          onClick={() => setOpen((value) => !value)}
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            className="size-5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            {open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
          </svg>
        </button>
      </div>

      {open && (
        <div id="mobile-menu" className="border-t border-white/10 bg-ink md:hidden">
          <nav aria-label="Мобильная навигация" className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-3">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={close}
                aria-current={isActive(item.href) ? "page" : undefined}
                className={cn(
                  "rounded-lg px-3 py-3 text-base font-medium",
                  isActive(item.href) ? "text-gold" : "text-snow/80",
                )}
              >
                {item.label}
              </Link>
            ))}
            <AccountActions layout="mobile" onNavigate={close} />
          </nav>
        </div>
      )}
    </header>
  );
}