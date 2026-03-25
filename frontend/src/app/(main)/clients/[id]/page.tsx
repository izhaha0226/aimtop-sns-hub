"use client";

import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/common/Button";
import { Input } from "@/components/common/Input";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { useToast } from "@/components/common/Toast";
import { useClient, useUpdateClient } from "@/hooks/useClients";

const clientEditSchema = z.object({
  name: z.string().min(1, "이름을 입력해주세요"),
  account_type: z.string().optional(),
  brand_color: z.string().optional(),
});

type ClientEditFormData = z.infer<typeof clientEditSchema>;

export default function ClientDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { data: client, isLoading } = useClient(id);

  if (isLoading) {
    return <LoadingSpinner className="mt-12" />;
  }

  if (!client) {
    return (
      <p className="mt-12 text-center text-gray-500">
        클라이언트를 찾을 수 없습니다.
      </p>
    );
  }

  return (
    <div>
      <BackButton />
      <ClientEditForm
        id={id}
        defaultValues={{
          name: client.name,
          account_type: client.account_type ?? "",
          brand_color: client.brand_color ?? "#000000",
        }}
      />
    </div>
  );
}

function BackButton() {
  const router = useRouter();

  return (
    <button
      onClick={() => router.push("/clients")}
      className="mb-4 flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"
    >
      <ArrowLeft className="h-4 w-4" />
      돌아가기
    </button>
  );
}

function ClientEditForm({
  id,
  defaultValues,
}: {
  id: string;
  defaultValues: ClientEditFormData;
}) {
  const updateClient = useUpdateClient();
  const { toast } = useToast();
  const router = useRouter();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ClientEditFormData>({
    resolver: zodResolver(clientEditSchema),
    defaultValues,
  });

  const onSubmit = (data: ClientEditFormData) => {
    updateClient.mutate(
      { id, data },
      {
        onSuccess: () => {
          toast({
            title: "클라이언트가 수정되었습니다.",
            variant: "success",
          });
          router.push("/clients");
        },
        onError: () => {
          toast({ title: "수정에 실패했습니다.", variant: "error" });
        },
      }
    );
  };

  return (
    <div className="max-w-md rounded-lg bg-white p-6 shadow-sm">
      <h1 className="mb-4 text-xl font-bold text-gray-900">
        클라이언트 수정
      </h1>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="이름"
          error={errors.name?.message}
          {...register("name")}
        />
        <Input
          label="계정 유형"
          {...register("account_type")}
        />
        <Input
          label="브랜드 컬러"
          type="color"
          {...register("brand_color")}
        />
        <div className="flex gap-2 pt-2">
          <Button type="submit" loading={updateClient.isPending}>
            저장
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push("/clients")}
          >
            취소
          </Button>
        </div>
      </form>
    </div>
  );
}
