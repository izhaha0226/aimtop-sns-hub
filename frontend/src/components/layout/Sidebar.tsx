"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  FileText,
  Calendar,
  MessageSquare,
  BarChart3,
  TrendingUp,
  Settings,
  Building2,
  Menu,
  X,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/utils/cn";
import { ROUTES } from "@/constants/routes";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  disabled: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { label: "대시보드", href: ROUTES.DASHBOARD, icon: Home, disabled: false },
  { label: "콘텐츠", href: ROUTES.CONTENTS, icon: FileText, disabled: true },
  { label: "캘린더", href: ROUTES.CALENDAR, icon: Calendar, disabled: true },
  { label: "인박스", href: ROUTES.INBOX, icon: MessageSquare, disabled: true },
  { label: "분석", href: ROUTES.ANALYTICS, icon: BarChart3, disabled: true },
  { label: "Growth Hub", href: ROUTES.GROWTH, icon: TrendingUp, disabled: true },
  { label: "클라이언트", href: ROUTES.CLIENTS, icon: Building2, disabled: false },
  { label: "설정", href: ROUTES.SETTINGS_USERS, icon: Settings, disabled: false },
];

export function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      <MobileToggle onToggle={() => setMobileOpen(true)} />
      <MobileOverlay
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
      />
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-60 border-r border-gray-200 bg-white transition-transform lg:static lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <SidebarContent onClose={() => setMobileOpen(false)} />
      </aside>
    </>
  );
}

function MobileToggle({ onToggle }: { onToggle: () => void }) {
  return (
    <button
      className="fixed left-4 top-4 z-50 rounded-md p-2 text-gray-600 lg:hidden"
      onClick={onToggle}
      aria-label="Open sidebar"
    >
      <Menu className="h-6 w-6" />
    </button>
  );
}

function MobileOverlay({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-30 bg-black/50 lg:hidden"
      onClick={onClose}
    />
  );
}

function SidebarContent({ onClose }: { onClose: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <SidebarHeader onClose={onClose} />
      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.href} item={item} />
        ))}
      </nav>
    </div>
  );
}

function SidebarHeader({ onClose }: { onClose: () => void }) {
  return (
    <div className="flex h-16 items-center justify-between border-b border-gray-200 px-4">
      <span className="text-lg font-bold text-gray-900">SNS Hub</span>
      <button
        className="rounded-md p-1 text-gray-400 hover:text-gray-600 lg:hidden"
        onClick={onClose}
        aria-label="Close sidebar"
      >
        <X className="h-5 w-5" />
      </button>
    </div>
  );
}

function NavLink({ item }: { item: NavItem }) {
  const pathname = usePathname();
  const isActive = pathname.startsWith(item.href);

  if (item.disabled) {
    return (
      <span className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-gray-400 cursor-not-allowed">
        <item.icon className="h-5 w-5" />
        {item.label}
        <span className="ml-auto text-xs">준비중</span>
      </span>
    );
  }

  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        isActive
          ? "bg-blue-50 text-blue-700"
          : "text-gray-700 hover:bg-gray-100"
      )}
    >
      <item.icon className="h-5 w-5" />
      {item.label}
    </Link>
  );
}
