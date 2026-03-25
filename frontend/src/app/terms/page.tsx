export default function TermsPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-8">서비스 이용약관</h1>
      <p className="text-sm text-gray-500 mb-8">최종 수정일: 2026년 3월 26일</p>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">제1조 (목적)</h2>
        <p className="text-gray-700 leading-relaxed">
          본 약관은 에임탑(이하 "회사")이 제공하는 AimTop SNS Hub 서비스(이하 "서비스")의
          이용 조건 및 절차, 회사와 이용자 간의 권리·의무 및 책임 사항을 규정함을 목적으로 합니다.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">제2조 (서비스 내용)</h2>
        <p className="text-gray-700 leading-relaxed">
          서비스는 SNS 콘텐츠 자동화, 예약 발행, 성과 분석 등 소셜미디어 관리 도구를 제공합니다.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">제3조 (이용자 의무)</h2>
        <ul className="list-disc pl-5 text-gray-700 space-y-1">
          <li>각 SNS 플랫폼의 이용 약관을 준수해야 합니다.</li>
          <li>타인의 권리를 침해하는 콘텐츠를 발행해서는 안 됩니다.</li>
          <li>계정 정보를 타인에게 제공해서는 안 됩니다.</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">제4조 (면책 조항)</h2>
        <p className="text-gray-700 leading-relaxed">
          회사는 SNS 플랫폼의 정책 변경, API 중단 등 외부 요인으로 인한 서비스 중단에 대해
          책임을 지지 않습니다.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">제5조 (문의)</h2>
        <p className="text-gray-700">
          이메일: contact@aimtop.ai
        </p>
      </section>
    </div>
  )
}
