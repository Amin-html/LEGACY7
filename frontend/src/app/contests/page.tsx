import type { Metadata } from "next";

import { Catalog } from "@/components/contests/catalog";

export const metadata: Metadata = { title: "Конкурсы" };

export default function ContestsPage() {
  return <Catalog />;
}