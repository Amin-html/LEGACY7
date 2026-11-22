"use client";

import { useId } from "react";
import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  hint?: string;
};

export function Input({ label, error, hint, id, className, ...props }: InputProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const messageId = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;

  return (
    <div className="space-y-1.5">
      <label htmlFor={inputId} className="text-sm font-medium text-snow">
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={messageId}
        className={cn(
          "h-11 w-full rounded-xl border bg-ink/60 px-4 text-snow transition placeholder:text-muted/70 focus:border-gold",
          error ? "border-danger" : "border-white/15",
          className,
        )}
        {...props}
      />
      {error ? (
        <p id={messageId} role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : hint ? (
        <p id={messageId} className="text-sm text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}