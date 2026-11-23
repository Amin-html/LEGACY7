"use client";

import { isAxiosError } from "axios";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";

type Result<T> = { key: string; data: T | null; failed: boolean; status: number | null };

/**
 * Загружает данные с API. Загрузка считается по ключу запроса: пока ответ не пришёл
 * именно на текущий url, loading = true. Устаревшие ответы отбрасываются.
 */
export function useApiData<T>(url: string | null) {
  const [nonce, setNonce] = useState(0);
  const [result, setResult] = useState<Result<T> | null>(null);
  const key = url ? `${url}#${nonce}` : null;

  useEffect(() => {
    if (!url || !key) return;
    let ignore = false;
    api
      .get<T>(url)
      .then((response) => {
        if (!ignore) setResult({ key, data: response.data, failed: false, status: response.status });
      })
      .catch((error: unknown) => {
        if (ignore) return;
        const status = isAxiosError(error) ? (error.response?.status ?? 0) : 0;
        setResult({ key, data: null, failed: true, status });
      });
    return () => {
      ignore = true;
    };
  }, [url, key]);

  const current = key && result?.key === key ? result : null;
  const reload = useCallback(() => setNonce((value) => value + 1), []);

  return {
    data: current?.data ?? null,
    error: current?.failed ?? false,
    status: current?.status ?? null,
    loading: Boolean(url) && !current,
    reload,
  };
}