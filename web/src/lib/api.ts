// Types mirror the Pydantic models in api/app/models. Requests go through the /api rewrite.

export type StepKind = "user_message" | "assistant_message" | "tool_call" | "tool_result" | "escalation";

export interface AgentStep {
  step_no: number;
  kind: StepKind;
  tool_name: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface CustomerRef {
  customer_id: number | null;
  customer_name: string | null;
  account_no: string | null;
  phone: string | null;
  service_type: string | null;
  area_name: string | null;
}

export interface ConversationSummary extends CustomerRef {
  id: number;
  status: string;
  channel: string;
  created_at: string;
  last_activity: string;
  step_count: number;
  tool_calls: number;
  last_message: string | null;
}

export interface Ticket {
  id: number;
  customer_id: number;
  conversation_id: number | null;
  category: string;
  priority: string;
  summary: string;
  status: string;
  created_at: string;
}

export interface ConversationDetail extends CustomerRef {
  id: number;
  status: string;
  channel: string;
  created_at: string;
  steps: AgentStep[];
  tickets: Ticket[];
}

export interface TicketQueueItem extends CustomerRef {
  id: number;
  conversation_id: number | null;
  category: string;
  priority: string;
  summary: string;
  status: string;
  created_at: string;
}

export type TicketStatus = "open" | "in_progress" | "closed";

export interface SmsOutboxItem {
  id: number;
  customer_id: number | null;
  customer_name: string | null;
  to_phone: string;
  body: string;
  status: string;
  provider_sid: string | null;
  created_at: string;
}

export interface ChatResponse {
  conversation_id: number;
  reply: string;
  status: string;
  tools_called: string[];
  steps: AgentStep[];
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // not JSON; keep statusText
    }
    throw new ApiError(res.status, detail || `HTTP ${res.status}`);
  }
  return res.json();
}

const query = (params: Record<string, string | undefined>) => {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]);
  return q.size ? `?${q}` : "";
};

export const api = {
  conversations: (status?: string) => request<ConversationSummary[]>(`/conversations${query({ status })}`),
  conversation: (id: number) => request<ConversationDetail>(`/conversations/${id}`),
  tickets: (status?: string) => request<TicketQueueItem[]>(`/tickets${query({ status })}`),
  updateTicket: (id: number, status: TicketStatus) =>
    request<TicketQueueItem>(`/tickets/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  sms: () => request<SmsOutboxItem[]>("/sms"),
  chat: (message: string, conversation_id: number | null) =>
    request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify({ message, conversation_id }) }),
};
