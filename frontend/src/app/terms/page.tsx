export default function TermsPage() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-12 text-slate-900">
      <article className="mx-auto max-w-4xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="mb-2 text-sm font-semibold text-blue-600">AimTop SNS Hub</p>
        <h1 className="mb-3 text-3xl font-bold">서비스 이용약관</h1>
        <p className="mb-8 text-sm text-slate-500">시행일 및 최종 수정일: 2026년 5월 3일</p>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">제1조 목적</h2>
          <p className="leading-relaxed text-slate-700">
            본 약관은 에임탑(이하 “회사”)이 제공하는 AimTop SNS Hub(이하 “서비스”)의 이용 조건,
            절차, 회사와 이용자 간 권리·의무 및 책임 사항을 정하는 것을 목적으로 합니다.
          </p>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">제2조 서비스 내용</h2>
          <ul className="list-disc space-y-2 pl-5 text-slate-700">
            <li>SNS 콘텐츠 기획, 초안 생성, 카드뉴스/이미지 생성 보조</li>
            <li>Instagram, Facebook, Threads, X, LinkedIn, YouTube, TikTok, Kakao, Blog 등 채널 연동</li>
            <li>콘텐츠 저장, 예약 발행, 발행 이력 관리</li>
            <li>성과 분석, 벤치마킹, 운영계획 생성, 리포트 제공</li>
            <li>기타 회사가 정하는 SNS 운영 자동화 및 관리 기능</li>
          </ul>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">제3조 계정 및 인증</h2>
          <p className="leading-relaxed text-slate-700">
            이용자는 정확한 정보를 제공해야 하며, 계정 및 인증수단을 안전하게 관리해야 합니다.
            이용자의 관리 소홀로 발생한 손해에 대해서는 회사가 책임지지 않습니다. 외부 SNS 채널 연동은
            각 플랫폼의 OAuth 및 API 정책에 따릅니다.
          </p>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">제4조 이용자의 의무</h2>
          <ul className="list-disc space-y-2 pl-5 text-slate-700">
            <li>관련 법령과 각 SNS 플랫폼의 약관 및 정책을 준수해야 합니다.</li>
            <li>타인의 저작권, 상표권, 초상권, 개인정보 등 권리를 침해하는 콘텐츠를 등록·발행해서는 안 됩니다.</li>
            <li>허위·기만 광고, 불법 정보, 혐오·폭력·음란 콘텐츠 등 부적절한 콘텐츠를 생성하거나 발행해서는 안 됩니다.</li>
            <li>서비스의 보안, 운영 안정성, 다른 이용자의 이용을 방해해서는 안 됩니다.</li>
          </ul>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">제5조 콘텐츠와 발행 책임</h2>
          <p className="leading-relaxed text-slate-700">
            서비스가 생성하는 AI 초안, 이미지, 운영계획, 벤치마킹 분석은 이용자의 검토를 돕는 자료입니다.
            최종 게시 여부, 문구, 이미지, 광고성 표시, 법적 적합성, 플랫폼 정책 준수 여부는 이용자가 확인해야 합니다.
            회사는 외부 플랫폼의 정책 변경, 심사 거절, API 제한, 게시물 삭제 또는 계정 제재에 대해 책임을 지지 않습니다.
          </p>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">제6조 서비스 변경 및 중단</h2>
          <p className="leading-relaxed text-slate-700">
            회사는 서비스 개선, 보안, 장애 대응, 외부 플랫폼 API 변경, 설비 점검 등의 사유로 서비스의 전부 또는
            일부를 변경하거나 일시 중단할 수 있습니다. 중요한 변경 사항은 가능한 범위에서 사전에 안내합니다.
          </p>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">제7조 개인정보 및 데이터 삭제</h2>
          <p className="leading-relaxed text-slate-700">
            개인정보 처리에 관한 사항은 개인정보처리방침을 따릅니다. 이용자는 개인정보 및 연결된 SNS 데이터의
            삭제를 요청할 수 있으며, 절차는 아래 공개 URL에서 확인할 수 있습니다.
          </p>
          <a className="font-medium text-blue-600 underline" href="/data-deletion">
            https://sns.aimtop.ai/data-deletion
          </a>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">제8조 책임 제한</h2>
          <p className="leading-relaxed text-slate-700">
            회사는 천재지변, 네트워크 장애, 외부 플랫폼 장애, 이용자 귀책 사유 등 회사가 통제하기 어려운 사유로
            발생한 손해에 대해 책임을 지지 않습니다. 회사의 책임은 관련 법령이 허용하는 범위 내에서 제한됩니다.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">제9조 문의</h2>
          <p className="leading-relaxed text-slate-700">
            서비스 및 약관 문의: izhaha@aimtop.ai<br />
            개인정보 문의: izhaha@aimtop.ai
          </p>
        </section>
      </article>
    </main>
  )
}
