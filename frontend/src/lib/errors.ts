import { isAxiosError } from "axios";

export type FormErrors = { fields: Record<string, string>; message: string | null };

export const NO_ERRORS: FormErrors = { fields: {}, message: null };

/** Превращает ответ DRF в ошибки по полям и общее сообщение. */
export function parseApiError(error: unknown): FormErrors {
  const result: FormErrors = { fields: {}, message: null };

  if (!isAxiosError(error)) {
    result.message = "Что-то пошло не так. Попробуй ещё раз.";
    return result;
  }
  if (!error.response) {
    result.message = "Нет связи с сервером. Проверь подключение.";
    return result;
  }
  if (error.response.status === 429) {
    result.message = "Слишком много попыток. Подожди минуту.";
    return result;
  }

  const data: unknown = error.response.data;
  if (data && typeof data === "object") {
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      const text = Array.isArray(value)
        ? value.filter((item): item is string => typeof item === "string").join(" ")
        : typeof value === "string"
          ? value
          : "";
      if (!text) continue;
      if (key === "detail" || key === "non_field_errors") result.message = text;
      else result.fields[key] = text;
    }
  }

  if (!result.message && Object.keys(result.fields).length === 0) {
    result.message =
      error.response.status === 401 ? "Неверный email или пароль." : "Не удалось выполнить запрос.";
  }
  return result;
}