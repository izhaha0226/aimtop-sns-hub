export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-8">개인정보처리방침</h1>
      <p className="text-sm text-gray-500 mb-8">최종 수정일: 2026년 3월 26일</p>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">1. 수집하는 개인정보 항목</h2>
        <p className="text-gray-700 leading-relaxed">
          AimTop SNS Hub(이하 "서비스")는 서비스 제공을 위해 다음과 같은 개인정보를 수집합니다.
        </p>
        <ul className="list-disc pl-5 mt-3 text-gray-700 space-y-1">
          <li>이름, 이메일 주소, 연락처</li>
          <li>SNS 계정 연동 정보 (OAuth 토큰)</li>
          <li>서비스 이용 기록, 접속 로그</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">2. 개인정보의 수집 및 이용 목적</h2>
        <ul className="list-disc pl-5 text-gray-700 space-y-1">
          <li>서비스 회원 관리 및 본인 확인</li>
          <li>SNS 채널 자동화 서비스 제공</li>
          <li>서비스 개선 및 신규 기능 개발</li>
          <li>법령 준수 및 분쟁 해결</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">3. 개인정보의 보유 및 이용 기간</h2>
        <p className="text-gray-700 leading-relaxed">
          서비스 이용 기간 동안 보유하며, 탈퇴 시 지체 없이 파기합니다.
          단, 관계 법령에 따라 일정 기간 보존이 필요한 경우 해당 기간 동안 보관합니다.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">4. SNS 계정 연동 및 OAuth 토큰</h2>
        <p className="text-gray-700 leading-relaxed">
          서비스는 Meta, X, TikTok, LinkedIn, YouTube, Kakao 등 플랫폼의 OAuth 2.0 방식으로만
          계정을 연동합니다. 사용자의 계정 비밀번호는 수집하지 않으며, OAuth 토큰은
          AES-256으로 암호화하여 보관합니다.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">5. 개인정보의 제3자 제공</h2>
        <p className="text-gray-700 leading-relaxed">
          서비스는 사용자의 동의 없이 개인정보를 제3자에게 제공하지 않습니다.
          단, 법령에 의한 경우는 예외로 합니다.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">6. 이용자 권리</h2>
        <p className="text-gray-700 leading-relaxed">
          이용자는 언제든지 개인정보 조회, 수정, 삭제, 처리 정지를 요청할 수 있습니다.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">7. 개인정보 보호 책임자</h2>
        <p className="text-gray-700">
          회사명: 에임탑<br />
          이메일: privacy@aimtop.ai<br />
          전화: 문의 이메일로 연락 바랍니다
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">8. 개인정보처리방침 변경</h2>
        <p className="text-gray-700 leading-relaxed">
          본 방침은 법령 또는 서비스 변경에 따라 개정될 수 있으며,
          변경 시 서비스 내 공지를 통해 안내합니다.
        </p>
      </section>
    </div>
  )
}
