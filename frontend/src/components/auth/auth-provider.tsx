"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, refreshAccessToken, SESSION_EXPIRED_EVENT } from "@/lib/api";
import { setAccessToken } from "@/lib/token";
import type { User } from "@/lib/types";

type Status = "loading" | "authenticated" | "anonymous";

export type RegisterInput = {
  email: string;
  username: string;
  password: string;
  role: "participant" | "organizer";
};

type AuthContextValue = {
  user: User | null;
  status: Status;
  login: (email: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<Status>("loading");

  const applyUser = useCallback((next: User) => {
    setUser(next);
    setStatus("authenticated");
  }, []);

  const clear = useCallback(() => {
    setAccessToken(null);
    setUser(null);
    setStatus("anonymous");
  }, []);

  // При загрузке страницы пробуем восстановить сессию по refresh-cookie
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = await refreshAccessToken();
      if (!token) {
        if (!cancelled) setStatus("anonymous");
        return;
      }
      try {
        const { data } = await api.get<User>("/users/me/");
        if (!cancelled) applyUser(data);
      } catch {
        if (!cancelled) clear();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applyUser, clear]);

  useEffect(() => {
    window.addEventListener(SESSION_EXPIRED_EVENT, clear);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, clear);
  }, [clear]);

  const fetchMe = useCallback(async () => {
    const { data } = await api.get<User>("/users/me/");
    applyUser(data);
  }, [applyUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      const { data } = await api.post<{ access: string }>("/auth/login/", { email, password });
      setAccessToken(data.access);
      await fetchMe();
    },
    [fetchMe],
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      await api.post("/auth/register/", input);
      await login(input.email, input.password);
    },
    [login],
  );

  const loginWithGoogle = useCallback(
    async (idToken: string) => {
      const { data } = await api.post<{ access: string; user: User; needs_onboarding: boolean }>(
        "/auth/google/",
        { id_token: idToken },
      );
      setAccessToken(data.access);
      applyUser({ ...data.user, onboarding_completed: !data.needs_onboarding });
    },
    [applyUser],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout/");
    } catch {
      // Даже если сервер недоступен, локальную сессию закрываем
    }
    clear();
  }, [clear]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, status, login, register, loginWithGoogle, logout, refreshUser: fetchMe }),
    [user, status, login, register, loginWithGoogle, logout, fetchMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth нужно вызывать внутри AuthProvider");
  return context;
}