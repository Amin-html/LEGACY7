"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/components/auth/auth-provider";

/** Для страниц входа и регистрации: уже вошедшего отправляем дальше. */
export function useRedirectIfAuthenticated(): void {
  const { user, status } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (status === "authenticated" && user) {
      router.replace(user.onboarding_completed ? "/" : "/onboarding");
    }
  }, [status, user, router]);
}

/** Для страницы онбординга: гость идёт на вход, прошедший онбординг идёт на главную. */
export function useOnboardingGuard(): void {
  const { user, status } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
    else if (status === "authenticated" && user?.onboarding_completed) router.replace("/");
  }, [status, user, router]);
}