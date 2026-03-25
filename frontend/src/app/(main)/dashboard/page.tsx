export default function DashboardPage() {
  const stats = [
    { label: "오늘 발행", value: "—" },
    { label: "승인 대기", value: "—" },
    { label: "이번 달 도달", value: "—" },
    { label: "팔로워 증감", value: "—" },
  ]

  return (
    <div>
      <h1 className="text-xl font-bold mb-6">대시보드</h1>
      <div className="grid grid-cols-4 gap-4 mb-6">
        {stats.map(({ label, value }) => (
          <div key={label} className="bg-white rounded-xl border p-4">
            <p className="text-sm text-gray-500">{label}</p>
            <p className="text-2xl font-bold mt-1 text-gray-300">{value}</p>
          </div>
        ))}
      </div>
      <div className="bg-white rounded-xl border p-8 text-center">
        <p className="text-gray-400 text-sm">채널을 연동하고 첫 콘텐츠를 만들어보세요</p>
      </div>
    </div>
  )
}
