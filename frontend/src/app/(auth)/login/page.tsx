"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/common/Button";
import { Input } from "@/components/common/Input";

const loginSchema = z.object({
  email: z.string().email("올바른 이메일 주소를 입력해주세요"),
  password: z.string().min(1, "비밀번호를 입력해주세요"),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login, loginError, isLoggingIn } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = (data: LoginFormData) => {
    login(data);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <LoginCard
        onSubmit={handleSubmit(onSubmit)}
        register={register}
        errors={errors}
        loginError={loginError}
        isLoggingIn={isLoggingIn}
      />
    </div>
  );
}

function LoginCard({
  onSubmit,
  register,
  errors,
  loginError,
  isLoggingIn,
}: {
  onSubmit: React.FormEventHandler<HTMLFormElement>;
  register: ReturnType<typeof useForm<LoginFormData>>["register"];
  errors: Record<string, { message?: string }>;
  loginError: Error | null;
  isLoggingIn: boolean;
}) {
  return (
    <div className="w-full max-w-sm rounded-lg bg-white p-8 shadow-md">
      <h1 className="mb-6 text-center text-2xl font-bold text-gray-900">
        SNS Hub
      </h1>
      <form onSubmit={onSubmit} className="space-y-4">
        <Input
          label="이메일"
          type="email"
          placeholder="email@example.com"
          error={errors.email?.message}
          {...register("email")}
        />
        <Input
          label="비밀번호"
          type="password"
          placeholder="비밀번호 입력"
          error={errors.password?.message}
          {...register("password")}
        />
        {loginError ? (
          <p className="text-sm text-red-600">{loginError.message}</p>
        ) : null}
        <Button type="submit" className="w-full" loading={isLoggingIn}>
          로그인
        </Button>
      </form>
    </div>
  );
}
