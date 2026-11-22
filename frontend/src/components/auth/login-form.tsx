"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { AuthShell, FormAlert, OrDivider } from "@/components/auth/auth-shell";
import { GoogleButton } from "@/components/auth/google-button";
import { useRedirectIfAuthenticated } from "@/components/auth/use-auth-redirect";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NO_ERRORS, parseApiError, type FormErrors } from "@/lib/errors";

export function LoginForm() {
  useRedirectIfAuthenticated();
  const { login, loginWithGoogle } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FormErrors>(NO_ERRORS);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    const fields: Record<string, string> = {};
    if (!email.trim()) fields.email = "Введи email.";
    if (!password) fields.password = "Введи пароль.";
    if (Object.keys(fields).length > 0) {
      setErrors({ fields, message: null });
      return;
    }

    setSubmitting(true);
    setErrors(NO_ERRORS);
    try {
      await login(email.trim(), password); // дальше перенаправит useRedirectIfAuthenticated
    } catch (error) {
      setErrors(parseApiError(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function onGoogle(idToken: string) {
    setErrors(NO_ERRORS);
    try {
      await loginWithGoogle(idToken);
    } catch (error) {
      setErrors(parseApiError(error));
    }
  }

  return (
    <AuthShell
      title="С возвращением!"
      subtitle="Войди, чтобы подавать работы и следить за рейтингом."
      footer={
        <>
          Нет аккаунта?{" "}
          <Link href="/register" className="text-gold hover:underline">
            Зарегистрироваться
          </Link>
        </>
      }
    >
      <GoogleButton onCredential={onGoogle} />
      <OrDivider />
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <FormAlert message={errors.message} />
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={errors.fields.email}
        />
        <Input
          label="Пароль"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={errors.fields.password}
        />
        <Button type="submit" size="lg" loading={submitting} className="w-full">
          Войти
        </Button>
      </form>
    </AuthShell>
  );
}