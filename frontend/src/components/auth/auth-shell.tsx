"use client";

import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

import { Card } from "@/components/ui/card";

type AuthShellProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
};

export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  const reduceMotion = useReducedMotion();
  return (
    <main className="flex min-h-[calc(100dvh-4rem)] items-center justify-center bg-linear-to-b from-navy to-ink px-4 py-12">
      <motion.div
        className="w-full max-w-md"
        initial={reduceMotion ? false : { opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        <Card className="p-6 sm:p-8">
          <h1 className="font-display text-2xl font-bold">{title}</h1>
          <p className="mt-1 text-sm text-muted">{subtitle}</p>
          <div className="mt-6 space-y-4">{children}</div>
        </Card>
        {footer && <p className="mt-4 text-center text-sm text-muted">{footer}</p>}
      </motion.div>
    </main>
  );
}

export function FormAlert({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p
      role="alert"
      className="rounded-xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger"
    >
      {message}
    </p>
  );
}

export function OrDivider() {
  return (
    <div className="flex items-center gap-3 text-xs uppercase tracking-widest text-muted">
      <span className="h-px flex-1 bg-white/10" />
      или
      <span className="h-px flex-1 bg-white/10" />
    </div>
  );
}