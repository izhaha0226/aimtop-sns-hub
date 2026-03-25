"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Building2, Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/common/Button";
import { Input } from "@/components/common/Input";
import { Modal } from "@/components/common/Modal";
import { EmptyState } from "@/components/common/EmptyState";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { useToast } from "@/components/common/Toast";
import {
  useClients,
  useCreateClient,
  useDeleteClient,
} from "@/hooks/useClients";
import type { Client } from "@/types/client";

const clientSchema = z.object({
  name: z.string().min(1, "클라이언트 이름을 입력해주세요"),
  account_type: z.string().optional(),
  brand_color: z.string().optional(),
});

type ClientFormData = z.infer<typeof clientSchema>;

export default function ClientsPage() {
  const [showAddModal, setShowAddModal] = useState(false);
  const { data: clients, isLoading } = useClients();

  if (isLoading) {
    return <LoadingSpinner className="mt-12" />;
  }

  return (
    <div>
      <PageHeader onAdd={() => setShowAddModal(true)} />
      <ClientGrid clients={clients ?? []} />
      <AddClientModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
      />
    </div>
  );
}

function PageHeader({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="mb-6 flex items-center justify-between">
      <h1 className="text-2xl font-bold text-gray-900">클라이언트 관리</h1>
      <Button onClick={onAdd}>추가</Button>
    </div>
  );
}

function ClientGrid({ clients }: { clients: Client[] }) {
  if (clients.length === 0) {
    return (
      <EmptyState
        icon={Building2}
        title="클라이언트가 없습니다"
        description="새 클라이언트를 추가해보세요."
      />
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {clients.map((client) => (
        <ClientCard key={client.id} client={client} />
      ))}
    </div>
  );
}

function ClientCard({ client }: { client: Client }) {
  const deleteClient = useDeleteClient();
  const { toast } = useToast();

  const handleDelete = () => {
    deleteClient.mutate(client.id, {
      onSuccess: () => {
        toast({ title: "클라이언트가 삭제되었습니다.", variant: "success" });
      },
      onError: () => {
        toast({ title: "삭제에 실패했습니다.", variant: "error" });
      },
    });
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">{client.name}</h3>
          {client.account_type ? (
            <p className="mt-1 text-sm text-gray-500">{client.account_type}</p>
          ) : null}
          <p className="mt-2 text-xs text-gray-400">
            {new Date(client.created_at).toLocaleDateString("ko-KR")}
          </p>
        </div>
        <CardActions onDelete={handleDelete} clientId={client.id} />
      </div>
    </div>
  );
}

function CardActions({
  onDelete,
  clientId,
}: {
  onDelete: () => void;
  clientId: string;
}) {
  return (
    <div className="flex gap-1">
      <a
        href={`/clients/${clientId}`}
        className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
      >
        <Pencil className="h-4 w-4" />
      </a>
      <button
        onClick={onDelete}
        className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}

function AddClientModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const createClient = useCreateClient();
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ClientFormData>({
    resolver: zodResolver(clientSchema),
  });

  const onSubmit = (data: ClientFormData) => {
    createClient.mutate(data, {
      onSuccess: () => {
        toast({ title: "클라이언트가 생성되었습니다.", variant: "success" });
        reset();
        onClose();
      },
      onError: () => {
        toast({ title: "생성에 실패했습니다.", variant: "error" });
      },
    });
  };

  return (
    <Modal open={open} onClose={onClose} title="클라이언트 추가">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="이름"
          error={errors.name?.message}
          {...register("name")}
        />
        <Input
          label="계정 유형"
          placeholder="예: 기업, 개인"
          {...register("account_type")}
        />
        <Input
          label="브랜드 컬러"
          type="color"
          {...register("brand_color")}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            취소
          </Button>
          <Button type="submit" loading={createClient.isPending}>
            생성
          </Button>
        </div>
      </form>
    </Modal>
  );
}
