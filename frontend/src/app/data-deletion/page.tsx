export default function DataDeletionPage() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-12 text-slate-900">
      <article className="mx-auto max-w-4xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="mb-2 text-sm font-semibold text-blue-600">AimTop SNS Hub</p>
        <h1 className="mb-3 text-3xl font-bold">사용자 데이터 삭제 안내</h1>
        <p className="mb-8 text-sm text-slate-500">User Data Deletion Instructions · 최종 수정일: 2026년 5월 3일</p>

        <section className="mb-8 rounded-xl border border-blue-100 bg-blue-50 p-5">
          <h2 className="mb-2 text-lg font-semibold text-blue-900">공개 데이터 삭제 URL</h2>
          <p className="leading-relaxed text-blue-900">
            Meta/Facebook 앱 검수 및 이용자 안내용 데이터 삭제 URL은 아래 주소입니다.
          </p>
          <p className="mt-3 break-all rounded-lg bg-white px-4 py-3 font-mono text-sm text-blue-700">
            https://sns.aimtop.ai/data-deletion
          </p>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">1. 서비스 안에서 SNS 연결 해제하기</h2>
          <ol className="list-decimal space-y-2 pl-5 text-slate-700">
            <li>AimTop SNS Hub에 로그인합니다.</li>
            <li>클라이언트 상세 화면으로 이동합니다.</li>
            <li>삭제하려는 채널(Facebook, Instagram, Threads 등)의 “연동 해제” 버튼을 누릅니다.</li>
            <li>연동 해제 시 서비스에 저장된 해당 채널의 OAuth 토큰은 비활성화 또는 삭제 처리됩니다.</li>
          </ol>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">2. 계정 및 전체 데이터 삭제 요청</h2>
          <p className="leading-relaxed text-slate-700">
            서비스 계정, 클라이언트 정보, 콘텐츠 초안, 예약 정보, SNS 연동 토큰 등 서비스에 저장된 데이터를
            삭제하려면 아래 이메일로 요청해 주세요.
          </p>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 text-slate-700">
            <p><strong>요청 이메일:</strong> privacy@aimtop.ai</p>
            <p><strong>메일 제목:</strong> AimTop SNS Hub 사용자 데이터 삭제 요청</p>
            <p><strong>포함 정보:</strong> 가입 이메일, 회사/브랜드명, 삭제할 SNS 플랫폼, 요청 범위</p>
          </div>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">3. 삭제 처리 범위</h2>
          <ul className="list-disc space-y-2 pl-5 text-slate-700">
            <li>회원 계정 및 권한 정보</li>
            <li>클라이언트/브랜드 운영 정보</li>
            <li>콘텐츠 초안, 카드뉴스 기획, 예약/발행 관리 데이터</li>
            <li>OAuth access token, refresh token, 연결 계정 ID/이름 등 SNS 연동 정보</li>
            <li>서비스 이용 중 생성된 로그 중 개인을 식별할 수 있는 정보</li>
          </ul>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">4. 삭제 처리 기한</h2>
          <p className="leading-relaxed text-slate-700">
            삭제 요청 접수 후 본인 확인 및 요청 범위 확인을 거쳐 원칙적으로 7영업일 이내 처리합니다.
            법령상 보관 의무가 있는 정보는 해당 기간 동안 분리 보관 후 파기합니다.
          </p>
        </section>

        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold">5. 외부 플랫폼 데이터</h2>
          <p className="leading-relaxed text-slate-700">
            AimTop SNS Hub에서 삭제되는 정보와 별도로, Facebook, Instagram, Threads 등 외부 플랫폼 자체에
            저장된 게시물, 계정 정보, 활동 기록은 각 플랫폼의 개인정보/계정 설정에서 직접 삭제해야 할 수 있습니다.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">6. 문의</h2>
          <p className="leading-relaxed text-slate-700">
            데이터 삭제, 개인정보, SNS 연동 해제 관련 문의는 privacy@aimtop.ai 로 보내주세요.
          </p>
        </section>
      </article>
    </main>
  )
}
