import { cn } from "@/lib/cn";

export function Logo({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 font-display text-lg font-bold tracking-[0.2em] text-snow",
        className,
      )}
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" className="size-6 text-gold" fill="currentColor">
        <path d="M3 19h18v2H3zM2 6l5 4 5-6 5 6 5-4-2 11H4L2 6z" />
      </svg>
      <span>
        LEGACY <span className="text-gold">7</span>
      </span>
    </span>
  );
}