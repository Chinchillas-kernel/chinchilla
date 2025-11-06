import { Link } from "react-router-dom";

const quickLinks = [
  {
    title: "일자리 매칭",
    description: "경험과 적성에 맞는 시니어 맞춤형 일자리를 찾아드립니다.",
    to: "/chat/job",
    icon: "🧰",
  },
  {
    title: "법률 상담",
    description: "상속, 임대차, 권리 보호 등 걱정되는 상황을 함께 살펴봐요.",
    to: "/chat/legal",
    icon: "⚖️",
  },
  {
    title: "노인 관련 뉴스",
    description: "최신 복지 제도와 정책 변화를 한눈에 정리해 드립니다.",
    to: "/chat/news",
    icon: "📰",
  },
  {
    title: "종합 노인 복지",
    description: "돌봄, 건강, 생활 지원까지 필요한 서비스를 연결해요.",
    to: "/chat/welfare",
    icon: "🤝",
  },
  {
    title: "금융사기 탐지",
    description: "의심되는 전화·문자를 진단하고 예방 방법을 안내합니다.",
    to: "/chat/scam_defense",
    icon: "🛡️",
  },
];

const serviceHighlights = [
  "복지 서비스 신청 절차를 단계별로 안내합니다.",
  "자주 헷갈리는 서류 준비와 제출 요령을 도와드립니다.",
  "부정수급 신고 방법과 필요한 준비 사항을 꼼꼼히 챙겨드려요.",
];

const tipExamples = [
  "서울에서 받을 수 있는 복지는 뭐가 있어?",
  "이번주 노인관련 뉴스 알려줘!",
  "자식이 2명인데 재산분할 조언해줘",
];

const Index = () => {
  return (
    <main className="flex-1 overflow-y-auto bg-background">
      <div className="mx-auto max-w-5xl px-6 py-10 space-y-10">
        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-primary via-primary/90 to-primary/80 p-8 text-white shadow-xl">
          <div className="absolute inset-0 opacity-20" aria-hidden>
            <div className="absolute -left-16 top-10 h-48 w-48 rounded-full bg-white/30 blur-3xl" />
            <div className="absolute -right-10 bottom-0 h-40 w-40 rounded-full bg-white/20 blur-3xl" />
          </div>
          <div className="relative flex flex-col gap-8 md:flex-row md:items-center md:justify-between">
            <div className="max-w-xl space-y-5">
              <span className="inline-flex items-center gap-2 rounded-full bg-white/20 px-4 py-1 text-sm font-semibold uppercase tracking-wider">
                맞춤 복지 도우미
              </span>
              <h1 className="text-3xl font-bold leading-tight md:text-4xl">
                똑똑한 복지 도우미 복지팡이!
              </h1>
              <p className="text-base md:text-lg md:leading-relaxed text-white/90">
                궁금한 복지 정보를 물어보면 필요한 서비스와 절차를 바로 안내해 드려요. 어렵고 복잡한 용어는
                쉽게 설명하고, 필요한 자료도 함께 챙겨드립니다.
              </p>
              <div className="flex flex-wrap gap-3">
                <Link
                  to="/chat/welfare"
                  className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-5 py-2 text-sm font-semibold text-primary transition hover:bg-white/80"
                >
                  복지 상담 시작하기
                </Link>
                <Link
                  to="/chat/scam_defense"
                  className="inline-flex items-center justify-center gap-2 rounded-full border border-white/60 px-5 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  금융사기 예방 알아보기
                </Link>
              </div>
            </div>
            <div className="relative w-full max-w-sm self-stretch md:self-auto">
              <div className="h-full rounded-2xl bg-white/10 p-6 backdrop-blur-lg ring-1 ring-white/30">
                <p className="mb-4 text-sm font-semibold uppercase tracking-wide text-white/80">
                  이런 서비스를 준비했어요
                </p>
                <ul className="space-y-3 text-sm text-white/90">
                  <li className="flex items-start gap-3">
                    <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/20">1</span>
                    <span>현재 상황을 물어보고 필요한 정보를 빠르게 찾습니다.</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/20">2</span>
                    <span>신청 절차와 준비물을 순서대로 안내합니다.</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/20">3</span>
                    <span>필요하면 관련 기관과 연락하는 방법도 알려드립니다.</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section className="space-y-6">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-foreground">지금 가장 많이 이용하는 서비스</h2>
              <p className="text-sm text-muted-foreground">궁금한 항목을 선택하면 바로 해당 채팅 페이지로 이동합니다.</p>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {quickLinks.map((link) => (
              <Link
                key={link.title}
                to={link.to}
                className="group relative flex h-full flex-col justify-between overflow-hidden rounded-2xl border border-border bg-card/90 p-6 shadow-sm transition hover:-translate-y-1 hover:border-primary/50 hover:shadow-lg"
              >
                <div className="flex items-center justify-between">
                  <span className="text-2xl">{link.icon}</span>
                  <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary opacity-0 transition group-hover:opacity-100">
                    바로가기
                  </span>
                </div>
                <div className="mt-6 space-y-2">
                  <h3 className="text-lg font-semibold text-foreground">{link.title}</h3>
                  <p className="text-sm text-muted-foreground">{link.description}</p>
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="grid gap-6 md:grid-cols-[2fr,1fr]">
          <div className="rounded-3xl border border-border bg-muted/30 p-8 shadow-sm">
            <h2 className="mb-4 text-2xl font-semibold text-foreground">복지팡이가 도와드릴 수 있는 일</h2>
            <p className="mb-6 text-muted-foreground">
              일상에서 마주하는 복지 관련 고민을 혼자 해결하지 마세요. 복지팡이가 상황을 듣고 가장 알맞은
              정보를 연결해 드립니다.
            </p>
            <ul className="space-y-3 text-sm text-muted-foreground">
              {serviceHighlights.map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="mt-1 h-2 w-2 rounded-full bg-primary" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-3xl border border-primary/40 bg-primary/5 p-7 shadow-sm">
            <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-primary">TIP</p>
            <h3 className="mb-4 text-lg font-semibold text-foreground">이렇게 질문해 보세요</h3>
            <ul className="space-y-3 text-sm text-muted-foreground">
              {tipExamples.map((example) => (
                <li key={example} className="rounded-xl bg-background/60 px-3 py-3">
                  {example}
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </main>
  );
};

export default Index;
