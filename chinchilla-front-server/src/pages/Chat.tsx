import { useState, useRef, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send } from "lucide-react";
import ProfileForm from "@/components/ProfileForm";
import { sendAgentQuery, type ConversationHistoryItem } from "@/lib/api";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const remarkGfmPlugin =
  (remarkGfm as unknown as { default?: unknown }).default ?? remarkGfm;

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<Record<string, unknown>>;
}

type ApiCategory = "jobs" | "welfare" | "news" | "legal" | "scam_defense";

type ProfileData = {
  age?: string;
  gender?: string;
  region?: string;
  income?: string;
  interests?: string[];
};

const CATEGORY_API_MAP: Record<string, ApiCategory | undefined> = {
  job: "jobs",
  jobs: "jobs",
  welfare: "welfare",
  news: "news",
  legal: "legal",
  scam_defense: "scam_defense",
};

const categoryInfo: Record<string, { title: string; description: string; requiresProfile?: boolean }> = {
  job: {
    title: "일자리 매칭",
    description: "맞춤형 노인 일자리를 추천해드립니다",
    requiresProfile: true,
  },
  legal: {
    title: "법률 상담",
    description: "법률 문제에 대해 상담해드립니다",
    requiresProfile: true,
  },
  news: {
    title: "노인 관련 뉴스",
    description: "관련된 뉴스를 알려드립니다"
  },
  welfare: {
    title: "종합 노인 복지",
    description: "복지 서비스를 확인해보세요"
  },
  scam_defense: {
    title: "금융사기 탐지",
    description: "의심되는 문자나,전화내용을 확인해보세요"
  }
};

const Chat = () => {
  const { category } = useParams<{ category: string }>();
  const [profileCompleted, setProfileCompleted] = useState(false);
  const [profileData, setProfileData] = useState<ProfileData | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "안녕하세요! 종합 복지 안내 서비스입니다.\n\n원하시는 지역에 대한 정보를 입력하시고, 공급하신 질문 질문해주세요.\n\n예시:\n- \"서울에서 운영하는 노인 주간보호 개설 지원사업 신청 조건이 궁금해요.\"\n- \"노인 화대 파괴 상담을 받을 수 있는 공공기관과 연락처 알려주.\"\n- \"이르신 교통비나 문화 이용권 같은 생활비 경감 지원이 있는지 알려줘.\""
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const categoryData = category ? categoryInfo[category] : null;
  const requiresProfile = categoryData?.requiresProfile && (category === "job" || category === "legal");

  useEffect(() => {
    // Reset profile state when category changes
    setProfileCompleted(false);
    setProfileData(null);
    setMessages([
      {
        id: "1",
        role: "assistant",
        content: requiresProfile 
          ? "안녕하세요! 먼저 프로필 정보를 입력해주세요." 
          : "안녕하세요! 무엇을 도와드릴까요?"
      }
    ]);
  }, [category, requiresProfile]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleProfileComplete = (data: ProfileData) => {
    setProfileData(data);
    setProfileCompleted(true);

    const hasProfileData = Boolean(
      data &&
        Object.values(data).some((value) => {
          if (Array.isArray(value)) {
            return value.length > 0;
          }
          return value !== undefined && value !== null && String(value).trim().length > 0;
        }),
    );

    const welcomeMessage: Message = {
      id: Date.now().toString(),
      role: "assistant",
      content: hasProfileData
        ? "프로필이 등록되었습니다. 이제 궁금하신 점을 질문해주세요!"
        : "안녕하세요! 무엇을 도와드릴까요?",
    };
    setMessages([welcomeMessage]);
  };

  const buildHistoryPayload = (): ConversationHistoryItem[] => {
    if (!messages.length) return [];
    const recent = messages.slice(-10);
    return recent.map((message) => ({
      role: message.role,
      content: message.content,
    }));
  };

  const buildProfilePayload = (apiCategory: ApiCategory): Record<string, unknown> | null => {
    if (!profileData) return null;

    if (apiCategory === "jobs") {
      const ageNumber = profileData.age ? Number.parseInt(profileData.age, 10) : undefined;
      const jobProfile: Record<string, unknown> = {
        age: Number.isFinite(ageNumber) ? ageNumber : undefined,
        gender: profileData.gender || "other",
        location: profileData.region,
      };

      Object.keys(jobProfile).forEach((key) => {
        if (jobProfile[key] === undefined || jobProfile[key] === null || jobProfile[key] === "") {
          delete jobProfile[key];
        }
      });

      return Object.keys(jobProfile).length ? jobProfile : null;
    }

    if (apiCategory === "legal") {
      const ageNumber = profileData.age ? Number.parseInt(profileData.age, 10) : undefined;
      const incomeBucket: Record<string, number> = {
        "under-100": 1_000_000,
        "100-200": 2_000_000,
        "200-300": 3_000_000,
        "300-500": 5_000_000,
        "over-500": 6_000_000,
      };

      const interestMap: Record<string, string> = {
        inheritance: "복지",
        realestate: "주거",
        finance: "연금",
        income: "의료",
      };

      const selectedInterest = profileData.interests?.[0];
      const legalProfile: Record<string, unknown> = {
        age: Number.isFinite(ageNumber) ? ageNumber : undefined,
        income: profileData.income ? incomeBucket[profileData.income] : undefined,
        interest: selectedInterest ? interestMap[selectedInterest] : undefined,
      };

      Object.keys(legalProfile).forEach((key) => {
        if (legalProfile[key] === undefined || legalProfile[key] === null) {
          delete legalProfile[key];
        }
      });

      return Object.keys(legalProfile).length ? legalProfile : null;
    }

    return null;
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    if (!category) return;

    const apiCategory = CATEGORY_API_MAP[category];
    if (!apiCategory) {
      const assistantMessage: Message = {
        id: `${Date.now()}-error`,
        role: "assistant",
        content: "지원하지 않는 카테고리입니다. 다른 항목을 선택해주세요.",
      };
      setMessages((prev) => [...prev, assistantMessage]);
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim()
    };

    const historyPayload = buildHistoryPayload();
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.value = "";
      textareaRef.current.dispatchEvent(new Event("input", { bubbles: true }));
    }
    setIsLoading(true);

    try {
      const profilePayload = buildProfilePayload(apiCategory);
      const response = await sendAgentQuery({
        category: apiCategory,
        query: userMessage.content,
        history: historyPayload,
        profile: profilePayload || undefined,
      });

      const assistantMessage: Message = {
        id: `${Date.now()}-assistant`,
        role: "assistant",
        content: response.answer,
        sources: response.sources,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Agent request failed", error);
      const assistantMessage: Message = {
        id: `${Date.now()}-error`,
        role: "assistant",
        content: "에이전트와 연결하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
      };
      setMessages(prev => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Show profile form if category requires it and profile is not completed
  if (requiresProfile && !profileCompleted) {
    return (
      <div className="flex flex-1 flex-col">
        <div className="border-b bg-background px-4 py-3">
          <h1 className="text-lg font-semibold">
            {categoryData?.title || "복지 챗봇"}
          </h1>
          {categoryData && (
            <p className="text-sm text-muted-foreground">
              {categoryData.description}
            </p>
          )}
        </div>
        <ProfileForm 
          category={category as "job" | "legal"} 
          onComplete={handleProfileComplete} 
        />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      {/* Header */}
      <div className="border-b bg-background px-4 py-3">
        <h1 className="text-lg font-semibold">
          {categoryData?.title || "복지 챗봇"}
        </h1>
        {categoryData && (
          <p className="text-sm text-muted-foreground">
            {categoryData.description}
          </p>
        )}
      </div>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-6">
          <div className="space-y-6">
            {messages.map((message) => {
              const isUser = message.role === "user";
              return (
                <div
                  key={message.id}
                  className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      isUser
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground"
                  }`}
                >
                  {isUser ? (
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">
                      {message.content}
                    </p>
                  ) : (
                    <div
                      className={cn(
                        "text-sm leading-relaxed whitespace-pre-wrap",
                        "break-words space-y-2 [&>p]:mb-2 [&>p:last-child]:mb-0",
                      )}
                    >
                      <ReactMarkdown
                        remarkPlugins={[remarkGfmPlugin]}
                        components={{
                          a: ({ node: _node, ...props }) => (
                            <a
                              {...props}
                              target="_blank"
                              rel="noreferrer"
                              className="underline"
                            />
                          ),
                          p: ({ node: _node, className, ...props }) => (
                            <p
                              {...props}
                              className={cn("mb-2 last:mb-0", className)}
                            />
                          ),
                          ul: ({ node: _node, className, ...props }) => (
                            <ul
                              {...props}
                              className={cn("mb-2 list-disc pl-4 last:mb-0", className)}
                            />
                          ),
                          ol: ({ node: _node, className, ...props }) => (
                            <ol
                              {...props}
                              className={cn("mb-2 list-decimal pl-4 last:mb-0", className)}
                            />
                          ),
                        }}
                      >
                        {message.content || ""}
                      </ReactMarkdown>
                    </div>
                  )}
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-3 space-y-1 text-xs text-muted-foreground">
                      <p className="font-semibold">참고 자료</p>
                      <ul className="list-disc space-y-1 pl-4">
                        {message.sources.map((source, index) => {
                          const title = typeof source.title === "string" ? source.title : undefined;
                          const url = typeof source.url === "string" ? source.url : undefined;
                          const label = title || url || `자료 ${index + 1}`;
                          return (
                            <li key={url || `${label}-${index}`} className="break-words">
                              {url ? (
                                <a
                                  href={url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="underline"
                                >
                                  {label}
                                </a>
                              ) : (
                                <span>{label}</span>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
              );
            })}
            {isLoading && (
              <div className="flex justify-start">
                <div className="max-w-[80%] rounded-2xl bg-muted px-4 py-3">
                  <div className="flex gap-1">
                    <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]"></div>
                    <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]"></div>
                    <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground"></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </main>

      {/* Input */}
      <div className="border-t bg-background">
        <div className="mx-auto max-w-3xl px-4 py-4">
          <div className="flex gap-3">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="메시지를 입력하세요..."
              className="min-h-[52px] max-h-32 resize-none rounded-xl border-border bg-muted/50"
              rows={1}
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              size="icon"
              className="h-[52px] w-[52px] shrink-0 rounded-xl"
            >
              <Send className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;
