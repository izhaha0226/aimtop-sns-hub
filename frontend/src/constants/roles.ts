export const ROLES = {
  ADMIN: "admin",
  APPROVER: "approver",
  EDITOR: "editor",
  VIEWER: "viewer",
} as const;

export type Role = (typeof ROLES)[keyof typeof ROLES];

export const ROLE_LABELS: Record<Role, string> = {
  admin: "관리자",
  approver: "승인자",
  editor: "편집자",
  viewer: "뷰어",
};

export const ROLE_COLORS: Record<Role, string> = {
  admin: "bg-red-100 text-red-800",
  approver: "bg-purple-100 text-purple-800",
  editor: "bg-blue-100 text-blue-800",
  viewer: "bg-gray-100 text-gray-800",
};
