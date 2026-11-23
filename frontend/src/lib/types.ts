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

export type LeaderRow = {
  place: number;
  user: { id: number; username: string };
  points: number;
  contests: number;
};