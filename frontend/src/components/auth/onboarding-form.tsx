"use client";

import { useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { AuthShell, FormAlert } from "@/components/auth/auth-shell";
import { RoleSelect, type SelfRole } from "@/components/auth/role-select";
import { useOnboardingGuard } from "@/components/auth/use-auth-redirect";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { NO_ERRORS, parseApiError, type FormErrors } from "@/lib/errors";

export function OnboardingForm() {
  useOnboardingGuard();
  const { user, refreshUser } = useAuth();
  const [username, setUsername] = useState(user?.username ?? "");
  const [role, setRole] = useState<SelfRole>("participant");
  const [errors, setErrors] = useState<FormErrors>(NO_ERRORS);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    if (!username.trim()) {
      setErrors({ fields: { username: "Придумай имя пользователя." }, message: null });
      return;
    }

    setSubmitting(true);
    setErrors(NO_ERRORS);
    try {
      await api.post("/users/me/onboarding/", { username: username.trim(), role });
      await refreshUser(); // после этого useOnboardingGuard отправит на главную
    } catch (error) {
      setErrors(parseApiError(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell title="Почти готово" subtitle="Выбери имя пользователя и роль. Это делается один раз.">
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <FormAlert message={errors.message} />
        <Input
          label="Имя пользователя"
          autoComplete="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          error={errors.fields.username}
        />
        <RoleSelect value={role} onChange={setRole} error={errors.fields.role} />
        <Button type="submit" size="lg" loading={submitting} className="w-full">
          Продолжить
        </Button>
      </form>
    </AuthShell>
  );
}