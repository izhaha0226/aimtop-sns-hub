"use client";

import { BarChart3, FileText, MessageSquare, Users } from "lucide-react";

export default function DashboardPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">대시보드</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={FileText} label="콘텐츠" value="-" />
        <StatCard icon={Users} label="클라이언트" value="-" />
        <StatCard icon={MessageSquare} label="미확인 메시지" value="-" />
        <StatCard icon={BarChart3} label="이번 주 게시물" value="-" />
      </div>
      <div className="mt-8 rounded-lg border border-gray-200 bg-white p-8 text-center">
        <p className="text-gray-500">대시보드 준비 중</p>
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-blue-50">
          <Icon className="h-5 w-5 text-blue-600" />
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-xl font-semibold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
}
