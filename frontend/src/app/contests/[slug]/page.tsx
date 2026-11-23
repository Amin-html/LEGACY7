import type { Metadata } from "next";
import { Suspense } from "react";

import { ContestView } from "@/components/contests/contest-view";

export const metadata: Metadata = { title: "Конкурс" };

function decodeSlug(raw: string): string {
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

async function ContestLoader({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <ContestView slug={decodeSlug(slug)} />;
}

export default function ContestPage({ params }: { params: Promise<{ slug: string }> }) {
  return (
    <Suspense fallback={<main className="mx-auto max-w-6xl px-4 py-10" aria-busy="true" />}>
      <ContestLoader params={params} />
    </Suspense>
  );
}