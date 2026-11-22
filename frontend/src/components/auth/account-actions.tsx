"use client";

import Link from "next/link";

import { useAuth } from "@/components/auth/auth-provider";
import { Button, buttonStyles } from "@/components/ui/button";

type AccountActionsProps = { layout: "desktop" | "mobile"; onNavigate?: () => void };

export function AccountActions({ layout, onNavigate }: AccountActionsProps) {
  const { user, status, logout } = useAuth();
  const mobile = layout === "mobile";

  if (status === "loading") {
    return <div aria-hidden="true" className={mobile ? "mt-2 h-11" : "h-9 w-40"} />;
  }

  if (user) {
    return (
      <div className={mobile ? "mt-2 flex items-center justify-between gap-3" : "flex items-center gap-3"}>
        <span className="truncate text-sm text-muted">{user.username}</span>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            onNavigate?.();
            void logout();
          }}
        >
          Выйти
        </Button>
      </div>
    );
  }

  return (
    <div className={mobile ? "mt-2 grid grid-cols-2 gap-3" : "flex items-center gap-3"}>
      <Link
        href="/login"
        onClick={onNavigate}
        className={buttonStyles({ variant: mobile ? "secondary" : "ghost", size: mobile ? "md" : "sm" })}
      >
        Войти
      </Link>
      <Link href="/register" onClick={onNavigate} className={buttonStyles({ size: mobile ? "md" : "sm" })}>
        Регистрация
      </Link>
    </div>
  );
}