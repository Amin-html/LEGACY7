"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { AuthShell, FormAlert, OrDivider } from "@/components/auth/auth-shell";
import { GoogleButton } from "@/components/auth/google-button";
import { RoleSelect, type SelfRole } from "@/components/auth/role-select";
import { useRedirectIfAuthenticated } from "@/components/auth/use-auth-redirect";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NO_ERRORS, parseApiError, type FormErrors } from "@/lib/errors";

export function RegisterForm() {
  useRedirectIfAuthenticated();
  const { register, loginWithGoogle } = useAuth();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [role, setRole] = useState<SelfRole>("participant");
  const [errors, setErrors] = useState<FormErrors>(NO_ERRORS);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    const fields: Record<string, string> = {};
    if (!email.includes("@")) fields.email = "Введи корректный email.";
    if (!username.trim()) fields.username = "Придумай имя пользователя.";
    if (password.length < 8) fields.password = "Минимум 8 символов.";
    if (confirm !== password) fields.confirm = "Пароли не совпадают.";
    if (Object.keys(fields).length > 0) {
      setErrors({ fields, message: null });
      return;
    }

    setSubmitting(true);
    setErrors(NO_ERRORS);
    try {
      await register({ email: email.trim(), username: username.trim(), password, role });
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
      title="Создай аккаунт"
      subtitle="Присоединяйся к LEGACY 7 и начни свой путь к победе."
      footer={
        <>
          Уже есть аккаунт?{" "}
          <Link href="/login" className="text-gold hover:underline">
            Войти
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
          label="Имя пользователя"
          autoComplete="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          error={errors.fields.username}
        />
        <Input
          label="Пароль"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={errors.fields.password}
          hint="Минимум 8 символов, не только цифры."
        />
        <Input
          label="Повтори пароль"
          type="password"
          autoComplete="new-password"
          value={confirm}
          onChange={(event) => setConfirm(event.target.value)}
          error={errors.fields.confirm}
        />
        <RoleSelect value={role} onChange={setRole} error={errors.fields.role} />
        <Button type="submit" size="lg" loading={submitting} className="w-full">
          Зарегистрироваться
        </Button>
      </form>
    </AuthShell>
  );
}