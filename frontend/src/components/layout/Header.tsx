"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Bell, ChevronDown, LogOut, User } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export function Header() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
      <WorkspaceSelector />
      <div className="flex items-center gap-4">
        <NotificationBell />
        <ProfileMenu />
      </div>
    </header>
  );
}

function WorkspaceSelector() {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100">
        <span>워크스페이스</span>
        <ChevronDown className="h-4 w-4" />
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="min-w-[180px] rounded-md border border-gray-200 bg-white p-1 shadow-md"
          sideOffset={5}
        >
          <DropdownMenu.Item className="cursor-pointer rounded-sm px-3 py-2 text-sm text-gray-500 outline-none">
            워크스페이스 준비중
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

function NotificationBell() {
  return (
    <button
      className="rounded-md p-2 text-gray-500 hover:bg-gray-100"
      aria-label="Notifications"
    >
      <Bell className="h-5 w-5" />
    </button>
  );
}

function ProfileMenu() {
  const { user, logout } = useAuth();

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
          {user?.name?.charAt(0) ?? "U"}
        </div>
        <span className="hidden sm:inline">{user?.name ?? "사용자"}</span>
        <ChevronDown className="h-4 w-4" />
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="min-w-[160px] rounded-md border border-gray-200 bg-white p-1 shadow-md"
          sideOffset={5}
          align="end"
        >
          <DropdownMenu.Item className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm text-gray-700 outline-none hover:bg-gray-100">
            <User className="h-4 w-4" />
            내 정보
          </DropdownMenu.Item>
          <DropdownMenu.Separator className="my-1 h-px bg-gray-200" />
          <DropdownMenu.Item
            className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm text-red-600 outline-none hover:bg-red-50"
            onSelect={logout}
          >
            <LogOut className="h-4 w-4" />
            로그아웃
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
