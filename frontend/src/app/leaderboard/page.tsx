import type { Metadata } from "next";

import { LeaderboardView } from "@/components/leaderboard/leaderboard-view";

export const metadata: Metadata = { title: "Рейтинг" };

export default function LeaderboardPage() {
  return <LeaderboardView />;
}