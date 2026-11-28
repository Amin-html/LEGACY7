import { Logo } from "@/components/logo";

/** Показывается, пока шапка не подгрузилась. Занимает то же место, чтобы страница не прыгала. */
export function HeaderFallback() {
  return (
    <header className="sticky top-0 z-50 h-16 border-b border-white/10 bg-ink/80 backdrop-blur">
      <div className="mx-auto flex h-full max-w-6xl items-center px-4">
        <Logo />
      </div>
    </header>
  );
}