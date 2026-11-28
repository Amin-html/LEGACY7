import type { Metadata, Viewport } from "next";
import { Inter, Montserrat } from "next/font/google";
import { Suspense, type ReactNode } from "react";

import { AuthProvider } from "@/components/auth/auth-provider";
import { Header } from "@/components/header";
import { HeaderFallback } from "@/components/header-fallback";

import "./globals.css";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
  display: "swap",
});

const montserrat = Montserrat({
  subsets: ["latin", "cyrillic"],
  variable: "--font-montserrat",
  weight: ["600", "700", "800"],
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "LEGACY 7", template: "%s | LEGACY 7" },
  description: "Платформа онлайн-конкурсов. Твой талант. Твоя победа.",
};

export const viewport: Viewport = {
  themeColor: "#07090d",
  colorScheme: "dark",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru" className={`${inter.variable} ${montserrat.variable}`}>
      <body className="min-h-dvh antialiased">
        <AuthProvider>
          <Suspense fallback={<HeaderFallback />}>
            <Header />
          </Suspense>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}