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