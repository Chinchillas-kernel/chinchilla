const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export type ConversationRole = "user" | "assistant";

export interface ConversationHistoryItem {
  role: ConversationRole;
  content: string;
}

export interface AgentQueryOptions {
  category: "jobs" | "welfare" | "news" | "legal" | "scam_defense";
  query: string;
  history?: ConversationHistoryItem[];
  profile?: Record<string, unknown>;
}

export interface AgentResponse {
  answer: string;
  sources: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
}

export async function sendAgentQuery({
  category,
  query,
  history = [],
  profile,
}: AgentQueryOptions): Promise<AgentResponse> {
  const payload: Record<string, unknown> = {
    category,
    payload: {
      query,
      history,
    },
  };

  if (profile && Object.keys(profile).length > 0) {
    payload.payload = {
      ...payload.payload,
      profile,
    };
  }

  const response = await fetch(`${API_BASE_URL}/agent/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Request failed");
  }

  const data = (await response.json()) as AgentResponse;
  return data;
}
