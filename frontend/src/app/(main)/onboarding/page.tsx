"use client"
import { useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { onboardingService } from "@/services/onboarding"
import Step1AccountType from "@/components/onboarding/Step1AccountType"
import Step2Tone from "@/components/onboarding/Step2Tone"
import Step3Channels from "@/components/onboarding/Step3Channels"
import Step4Benchmark from "@/components/onboarding/Step4Benchmark"
import Step5Complete from "@/components/onboarding/Step5Complete"

const STEPS = ["계정 유형", "톤앤매너", "채널 선택", "벤치마킹", "완료"]

export default function OnboardingPage() {
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const searchParams = useSearchParams()
  const router = useRouter()
  const clientId = searchParams.get("clientId") || ""

  async function handleStep1(accountType: string) {
    setLoading(true)
    try {
      await onboardingService.step1(clientId, accountType)
      setStep(2)
    } finally {
      setLoading(false)
    }
  }

  async function handleStep2(data: object) {
    setLoading(true)
    try {
      await onboardingService.step2(clientId, data)
      setStep(3)
    } finally {
      setLoading(false)
    }
  }

  async function handleStep3(channels: string[]) {
    setLoading(true)
    try {
      await onboardingService.step3(clientId, channels)
      setStep(4)
    } finally {
      setLoading(false)
    }
  }

  async function handleStep4(benchmarks: object[]) {
    setLoading(true)
    try {
      await onboardingService.step4(clientId, benchmarks)
      await onboardingService.complete(clientId)
      setStep(5)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* 진행 바 */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                ${i + 1 < step ? "bg-blue-600 text-white" :
                  i + 1 === step ? "bg-blue-600 text-white ring-4 ring-blue-100" :
                  "bg-gray-200 text-gray-400"}`}>
                {i + 1 < step ? "✓" : i + 1}
              </div>
              {i < STEPS.length - 1 && (
                <div className={`h-0.5 w-16 mx-1 ${i + 1 < step ? "bg-blue-600" : "bg-gray-200"}`} />
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-between">
          {STEPS.map((label) => (
            <span key={label} className="text-xs text-gray-400">{label}</span>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border p-8">
        {step === 1 && <Step1AccountType onNext={handleStep1} loading={loading} />}
        {step === 2 && <Step2Tone onNext={handleStep2} loading={loading} />}
        {step === 3 && <Step3Channels onNext={handleStep3} loading={loading} />}
        {step === 4 && <Step4Benchmark onNext={handleStep4} loading={loading} />}
        {step === 5 && <Step5Complete clientId={clientId} onDone={() => router.push("/dashboard")} />}
      </div>
    </div>
  )
}
