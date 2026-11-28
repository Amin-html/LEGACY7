export type Role = "participant" | "jury" | "organizer" | "admin";

export type User = {
  id: number;
  email: string;
  username: string;
  role: Role;
  is_email_verified: boolean;
  onboarding_completed: boolean;
  avatar: string | null;
  bio: string;
};

export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type Category = { id: number; name: string; slug: string };

export type ContestSummary = {
  id: number;
  slug: string;
  title: string;
  category: Category;
  organizer: string;
  cover: string | null;
  status: "published" | "judging" | "finished";
  is_open: boolean;
  starts_at: string;
  deadline: string;
  prize_pool: string;
  currency: string;
};

export type Prize = { place: number; amount: string; description: string };
export type Criterion = { id: number; title: string; max_score: number; weight: string };

export type ContestDetail = ContestSummary & {
  description: string;
  rules: string;
  public_submissions: boolean;
  prizes: Prize[];
  criteria: Criterion[];
};

export type ResultRow = {
  place: number;
  username: string;
  score: string;
  points: number;
  prize: string | null;
  title?: string;
};

export type ContestResultsData = {
  contest: { id: number; slug: string; title: string };
  results: ResultRow[];
};

export type LeaderRow = {
  place: number;
  user: { id: number; username: string };
  points: number;
  contests: number;
};