import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { getAccessToken, setAccessToken } from "@/lib/token";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export const SESSION_EXPIRED_EVENT = "legacy7:session-expired";

// withCredentials: браузер отправляет и принимает refresh-cookie
export const api = axios.create({ baseURL: API_URL, withCredentials: true, timeout: 15_000 });
// Отдельный клиент для refresh, чтобы не попасть в цикл перехватчиков
const bare = axios.create({ baseURL: API_URL, withCredentials: true, timeout: 15_000 });

let refreshing: Promise<string | null> | null = null;

/** Обновляет access по refresh-cookie. Параллельные вызовы делят один запрос. */
export function refreshAccessToken(): Promise<string | null> {
  if (!refreshing) {
    refreshing = bare
      .post<{ access: string }>("/auth/refresh/")
      .then((response) => {
        setAccessToken(response.data.access);
        return response.data.access;
      })
      .catch(() => {
        setAccessToken(null);
        return null;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.set("Authorization", `Bearer ${token}`);
  return config;
});

type RetryConfig = InternalAxiosRequestConfig & { _retried?: boolean };
const AUTH_PATHS = ["/auth/login/", "/auth/register/", "/auth/refresh/", "/auth/google/", "/auth/logout/"];

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryConfig | undefined;
    const isAuthCall = AUTH_PATHS.some((path) => config?.url?.startsWith(path));

    if (error.response?.status === 401 && config && !config._retried && !isAuthCall) {
      config._retried = true;
      const token = await refreshAccessToken();
      if (token) {
        config.headers.set("Authorization", `Bearer ${token}`);
        return api(config);
      }
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
    return Promise.reject(error);
  },
);