"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/common/Button";
import { Input } from "@/components/common/Input";
import { Modal } from "@/components/common/Modal";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { EmptyState } from "@/components/common/EmptyState";
import { useToast } from "@/components/common/Toast";
import { useAuth } from "@/hooks/useAuth";
import { ROLE_LABELS, ROLE_COLORS, type Role } from "@/constants/roles";
import * as usersService from "@/services/users";
import * as authService from "@/services/auth";
import type { User } from "@/types/user";

const inviteSchema = z.object({
  email: z.string().email("올바른 이메일을 입력해주세요"),
  name: z.string().min(1, "이름을 입력해주세요"),
  role: z.string().min(1, "역할을 선택해주세요"),
});

type InviteFormData = z.infer<typeof inviteSchema>;

export default function UsersSettingsPage() {
  const [showInviteModal, setShowInviteModal] = useState(false);
  const { user: currentUser } = useAuth();

  const { data: users, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: usersService.getUsers,
  });

  if (currentUser?.role !== "admin") {
    return <AccessDenied />;
  }

  if (isLoading) {
    return <LoadingSpinner className="mt-12" />;
  }

  return (
    <div>
      <UsersPageHeader onInvite={() => setShowInviteModal(true)} />
      <UsersTable users={users ?? []} />
      <InviteModal
        open={showInviteModal}
        onClose={() => setShowInviteModal(false)}
      />
    </div>
  );
}

function AccessDenied() {
  return (
    <EmptyState
      title="접근 권한이 없습니다"
      description="관리자만 접근할 수 있습니다."
    />
  );
}

function UsersPageHeader({ onInvite }: { onInvite: () => void }) {
  return (
    <div className="mb-6 flex items-center justify-between">
      <h1 className="text-2xl font-bold text-gray-900">사용자 관리</h1>
      <Button onClick={onInvite}>초대</Button>
    </div>
  );
}

function UsersTable({ users }: { users: User[] }) {
  if (users.length === 0) {
    return <EmptyState title="사용자가 없습니다" />;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <TableHead>이름</TableHead>
            <TableHead>이메일</TableHead>
            <TableHead>역할</TableHead>
            <TableHead>상태</TableHead>
            <TableHead>마지막 로그인</TableHead>
            <TableHead>작업</TableHead>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {users.map((user) => (
            <UserRow key={user.id} user={user} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TableHead({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
      {children}
    </th>
  );
}

function UserRow({ user }: { user: User }) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const deactivateMutation = useMutation({
    mutationFn: () => usersService.deactivateUser(user.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast({ title: "사용자가 비활성화되었습니다.", variant: "success" });
    },
    onError: () => {
      toast({ title: "비활성화에 실패했습니다.", variant: "error" });
    },
  });

  return (
    <tr>
      <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
        {user.name}
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
        {user.email}
      </td>
      <td className="whitespace-nowrap px-4 py-3">
        <RoleBadge role={user.role} />
      </td>
      <td className="whitespace-nowrap px-4 py-3">
        <StatusBadge status={user.status} />
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
        {user.last_login_at
          ? new Date(user.last_login_at).toLocaleDateString("ko-KR")
          : "-"}
      </td>
      <td className="whitespace-nowrap px-4 py-3">
        {user.status === "active" ? (
          <Button
            variant="danger"
            size="sm"
            onClick={() => deactivateMutation.mutate()}
            loading={deactivateMutation.isPending}
          >
            비활성화
          </Button>
        ) : (
          <span className="text-xs text-gray-400">비활성</span>
        )}
      </td>
    </tr>
  );
}

function RoleBadge({ role }: { role: Role }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${ROLE_COLORS[role]}`}
    >
      {ROLE_LABELS[role]}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const isActive = status === "active";
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
        isActive
          ? "bg-green-100 text-green-800"
          : "bg-gray-100 text-gray-800"
      }`}
    >
      {isActive ? "활성" : "비활성"}
    </span>
  );
}

function InviteModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { toast } = useToast();

  const inviteMutation = useMutation({
    mutationFn: authService.inviteUser,
    onSuccess: () => {
      toast({ title: "초대가 발송되었습니다.", variant: "success" });
      reset();
      onClose();
    },
    onError: () => {
      toast({ title: "초대에 실패했습니다.", variant: "error" });
    },
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<InviteFormData>({
    resolver: zodResolver(inviteSchema),
  });

  const onSubmit = (data: InviteFormData) => {
    inviteMutation.mutate(data);
  };

  return (
    <Modal open={open} onClose={onClose} title="사용자 초대">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="이름"
          error={errors.name?.message}
          {...register("name")}
        />
        <Input
          label="이메일"
          type="email"
          error={errors.email?.message}
          {...register("email")}
        />
        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">
            역할
          </label>
          <select
            className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            {...register("role")}
          >
            <option value="">역할 선택</option>
            <option value="admin">관리자</option>
            <option value="approver">승인자</option>
            <option value="editor">편집자</option>
            <option value="viewer">뷰어</option>
          </select>
          {errors.role?.message ? (
            <p className="text-xs text-red-600">{errors.role.message}</p>
          ) : null}
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            취소
          </Button>
          <Button type="submit" loading={inviteMutation.isPending}>
            초대
          </Button>
        </div>
      </form>
    </Modal>
  );
}
