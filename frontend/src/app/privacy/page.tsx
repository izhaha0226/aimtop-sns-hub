export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-12 text-slate-900">
      <article className="mx-auto max-w-4xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="mb-2 text-sm font-semibold text-blue-600">AimTop SNS Hub</p>
        <h1 className="mb-3 text-3xl font-bold">개인정보처리방침</h1>
        <p className="mb-8 text-sm text-slate-500">시행일 및 최종 수정일: 2026년 5월 3일</p>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">1. 총칙</h2>
          <p className="leading-relaxed text-slate-700">
            에임탑(이하 “회사”)은 AimTop SNS Hub(이하 “서비스”)를 제공하면서 이용자의 개인정보를
            중요하게 생각하며, 개인정보 보호 관련 법령을 준수합니다. 본 방침은 서비스가 어떤 정보를
            수집하고, 어떻게 이용·보관·삭제하는지 설명합니다.
          </p>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">2. 수집하는 개인정보 항목</h2>
          <ul className="list-disc space-y-2 pl-5 text-slate-700">
            <li>회원 정보: 이름, 이메일 주소, 회사/브랜드명, 권한 정보</li>
            <li>서비스 이용 정보: 로그인 기록, 접속 IP, 브라우저/기기 정보, 서비스 이용 로그</li>
            <li>고객/브랜드 운영 정보: 클라이언트명, 브랜드 설명, 운영 채널, 콘텐츠 기획/발행 데이터</li>
            <li>SNS 계정 연동 정보: OAuth access token, refresh token, 토큰 만료일, 연결 계정 ID/이름</li>
            <li>문의/지원 정보: 문의 내용, 처리 이력, 이메일 커뮤니케이션 기록</li>
          </ul>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">3. 개인정보 수집 및 이용 목적</h2>
          <ul className="list-disc space-y-2 pl-5 text-slate-700">
            <li>회원 인증, 계정 관리, 권한 관리</li>
            <li>SNS 채널 연동, 콘텐츠 생성, 예약 발행, 성과 분석 등 서비스 제공</li>
            <li>고객 지원, 오류 대응, 보안 모니터링, 부정 이용 방지</li>
            <li>서비스 품질 개선, 기능 개발, 통계 분석</li>
            <li>법령상 의무 이행 및 분쟁 대응</li>
          </ul>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">4. SNS 계정 연동 및 플랫폼 데이터</h2>
          <p className="leading-relaxed text-slate-700">
            서비스는 Meta(Facebook, Instagram, Threads), X, YouTube, TikTok, Kakao, LinkedIn, Naver Blog 등
            외부 플랫폼의 OAuth 인증을 통해 계정을 연동합니다. 회사는 이용자의 각 플랫폼 비밀번호를
            수집하지 않습니다. OAuth 토큰은 암호화하여 저장하며, 콘텐츠 발행·성과 조회·댓글 관리 등
            이용자가 요청한 기능 수행에만 사용합니다.
          </p>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">5. 보유 및 이용 기간</h2>
          <p className="leading-relaxed text-slate-700">
            개인정보는 서비스 이용 기간 동안 보유하며, 회원 탈퇴 또는 삭제 요청 시 지체 없이 파기합니다.
            단, 관계 법령에 따라 보존이 필요한 정보는 해당 법령에서 정한 기간 동안 분리 보관할 수 있습니다.
          </p>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">6. 제3자 제공 및 처리 위탁</h2>
          <p className="leading-relaxed text-slate-700">
            회사는 이용자의 동의 없이 개인정보를 제3자에게 제공하지 않습니다. 다만 서비스 제공을 위해
            클라우드 인프라, 이메일 발송, 분석, 외부 SNS 플랫폼 API 등 필요한 범위에서 처리 업무를
            위탁하거나 이용자가 직접 연결한 플랫폼으로 데이터를 전송할 수 있습니다.
          </p>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">7. 이용자의 권리와 데이터 삭제</h2>
          <p className="leading-relaxed text-slate-700">
            이용자는 언제든지 개인정보 열람, 정정, 삭제, 처리 정지, SNS 채널 연결 해제를 요청할 수 있습니다.
            데이터 삭제 절차는 아래 공개 URL에서 확인할 수 있습니다.
          </p>
          <a className="font-medium text-blue-600 underline" href="/data-deletion">
            https://sns.aimtop.ai/data-deletion
          </a>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">8. 개인정보 보호 조치</h2>
          <ul className="list-disc space-y-2 pl-5 text-slate-700">
            <li>OAuth 토큰 및 주요 인증정보 암호화 저장</li>
            <li>관리자 권한 및 접근 통제</li>
            <li>접속 기록 관리 및 보안 모니터링</li>
            <li>불필요한 개인정보 최소 수집 원칙 적용</li>
          </ul>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">9. 개인정보 보호 책임자</h2>
          <p className="leading-relaxed text-slate-700">
            회사명: 에임탑<br />
            문의 이메일: privacy@aimtop.ai<br />
            서비스 문의: contact@aimtop.ai
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">10. 방침 변경</h2>
          <p className="leading-relaxed text-slate-700">
            본 개인정보처리방침은 법령, 서비스 구조, 개인정보 처리 방식 변경에 따라 개정될 수 있으며,
            중요한 변경이 있을 경우 서비스 화면 또는 이메일을 통해 안내합니다.
          </p>
        </section>
      </article>
    </main>
  )
}
