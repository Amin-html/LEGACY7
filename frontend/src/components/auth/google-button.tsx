"use client";

import { useEffect, useRef, useState } from "react";

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";
const SCRIPT_SRC = "https://accounts.google.com/gsi/client";

type CredentialResponse = { credential?: string };
type GoogleIdentity = {
  initialize: (config: { client_id: string; callback: (response: CredentialResponse) => void }) => void;
  renderButton: (parent: HTMLElement, options: Record<string, string | number>) => void;
};

declare global {
  interface Window {
    google?: { accounts: { id: GoogleIdentity } };
  }
}

let scriptPromise: Promise<void> | null = null;

function loadGoogleScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!scriptPromise) {
    scriptPromise = new Promise<void>((resolve, reject) => {
      const script = document.createElement("script");
      script.src = SCRIPT_SRC;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => {
        scriptPromise = null;
        reject(new Error("Не удалось загрузить скрипт Google"));
      };
      document.head.appendChild(script);
    });
  }
  return scriptPromise;
}

export function GoogleButton({ onCredential }: { onCredential: (idToken: string) => void }) {
  const holder = useRef<HTMLDivElement>(null);
  const callback = useRef(onCredential);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    callback.current = onCredential;
  });

  useEffect(() => {
    if (!CLIENT_ID) return;
    let cancelled = false;
    loadGoogleScript()
      .then(() => {
        const element = holder.current;
        const google = window.google;
        if (cancelled || !element || !google) return;
        google.accounts.id.initialize({
          client_id: CLIENT_ID,
          callback: (response) => {
            if (response.credential) callback.current(response.credential);
          },
        });
        element.replaceChildren();
        google.accounts.id.renderButton(element, {
          type: "standard",
          theme: "filled_black",
          size: "large",
          text: "continue_with",
          shape: "pill",
          locale: "ru",
          width: Math.min(320, element.clientWidth || 320),
        });
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!CLIENT_ID) {
    return <p className="text-center text-sm text-muted">Вход через Google не настроен.</p>;
  }
  if (failed) {
    return <p className="text-center text-sm text-danger">Не удалось загрузить вход через Google.</p>;
  }
  return <div ref={holder} className="flex min-h-11 justify-center" />;
}