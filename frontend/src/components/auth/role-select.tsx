"use client";

import { cn } from "@/lib/cn";

const ROLES = [
  { value: "participant", title: "Участник", text: "Подаю работы на конкурсы" },
  { value: "organizer", title: "Организатор", text: "Создаю и веду конкурсы" },
] as const;

export type SelfRole = (typeof ROLES)[number]["value"];

type RoleSelectProps = {
  value: SelfRole;
  onChange: (role: SelfRole) => void;
  error?: string;
};

export function RoleSelect({ value, onChange, error }: RoleSelectProps) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">Роль</legend>
      <div className="grid grid-cols-2 gap-3">
        {ROLES.map((role) => (
          <label
            key={role.value}
            className={cn(
              "cursor-pointer rounded-xl border border-white/15 p-3 transition",
              "has-checked:border-gold has-checked:bg-gold/10 has-focus-visible:ring-2 has-focus-visible:ring-gold",
            )}
          >
            <input
              type="radio"
              name="role"
              value={role.value}
              checked={value === role.value}
              onChange={() => onChange(role.value)}
              className="sr-only"
            />
            <span className="block text-sm font-semibold">{role.title}</span>
            <span className="block text-xs text-muted">{role.text}</span>
          </label>
        ))}
      </div>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <p className="text-xs text-muted">Роль жюри выдаёт администратор.</p>
    </fieldset>
  );
}