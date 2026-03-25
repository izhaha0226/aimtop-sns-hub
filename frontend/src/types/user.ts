export interface User {
  id: string;
  name: string;
  email: string;
  phone?: string;
  telegram_id?: string;
  profile_image?: string;
  role: "admin" | "approver" | "editor" | "viewer";
  status: "active" | "inactive";
  last_login_at?: string;
  created_at: string;
  updated_at: string;
}
