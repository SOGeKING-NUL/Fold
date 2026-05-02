const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...init,
  });
  if (res.status === 401) {
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export interface AuthMeResponse {
  user_ref: string;
}

export interface DashboardSummary {
  income_minor: number;
  expense_minor: number;
  investment_minor: number;
  net_cashflow_minor: number;
}

export interface BreakdownRow {
  key: string;
  amount_minor: number;
}

export interface BalanceRow {
  code: string;
  name: string;
  account_type: string;
  balance_minor: number;
}

export interface Transaction {
  id: number;
  transaction_type: string;
  source: string;
  description: string;
  occurred_at: string;
  metadata_json: Record<string, unknown>;
  total_debit_minor: number;
  total_credit_minor: number;
}

export interface DailyTrendPoint {
  day: string;
  expense_minor: number;
  income_minor: number;
}

export interface DashboardData {
  period: string;
  period_label: string;
  window_days: number;
  summary: DashboardSummary;
  by_category: BreakdownRow[];
  by_payment_method: BreakdownRow[];
  by_account: BreakdownRow[];
  balances: BalanceRow[];
  daily_trend: DailyTrendPoint[];
  recent_transactions: Transaction[];
}

export interface TransactionsResponse {
  transactions: Transaction[];
  limit: number;
  offset: number;
}

export async function exchangeToken(token: string) {
  return apiFetch<{ status: string; user_ref: string }>(
    `/api/v1/web/auth/exchange?token=${encodeURIComponent(token)}`
  );
}

export async function login(userRef: string) {
  return apiFetch<{ status: string; user_ref: string }>("/api/v1/web/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_ref: userRef }),
  });
}

export async function getMe() {
  return apiFetch<AuthMeResponse>("/api/v1/web/auth/me");
}

export async function getDashboard(period: "weekly" | "monthly") {
  return apiFetch<DashboardData>(
    `/api/v1/web/dashboard?period=${period}`
  );
}

export async function getTransactions(limit = 50, offset = 0) {
  return apiFetch<TransactionsResponse>(
    `/api/v1/web/transactions?limit=${limit}&offset=${offset}`
  );
}

export async function logout() {
  return apiFetch<{ status: string }>("/api/v1/web/auth/logout", {
    method: "POST",
  });
}
