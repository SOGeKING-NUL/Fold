const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit & { token?: string }): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.token) {
    headers.set("Authorization", `Bearer ${init.token}`);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
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

export interface Account {
  id: number;
  name: string;
  account_type: string;
  balance: number;
  institution_name?: string;
  account_number_last4?: string;
  is_default?: boolean;
}

export interface Transaction {
  id: number;
  type: string;
  source: string;
  description: string;
  occurred_at: string;
  amount: number;
  category: string;
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
  accounts: Account[];
  daily_trend: DailyTrendPoint[];
  recent_transactions: Transaction[];
}

export interface TransactionsResponse {
  transactions: Transaction[];
  limit: number;
  offset: number;
}

export async function getMe(token: string) {
  return apiFetch<AuthMeResponse>("/api/v1/web/auth/me", { token });
}

export async function getDashboard(period: "weekly" | "monthly", token: string) {
  return apiFetch<DashboardData>(
    `/api/v1/web/dashboard?period=${period}`,
    { token }
  );
}

export async function getTransactions(limit: number, offset: number, token: string) {
  return apiFetch<TransactionsResponse>(
    `/api/v1/web/transactions?limit=${limit}&offset=${offset}`,
    { token }
  );
}

export interface PaymentProfile {
  id: number;
  provider: string;
  profile_name: string;
  linked_account_name: string;
}

export interface PaymentProfilesResponse {
  status: string;
  user_ref: string;
  profiles: PaymentProfile[];
}

export interface AccountUpsertRequest {
  user_ref: string;
  name: string;
  account_type: "cash" | "bank" | "credit";
  institution_name?: string;
  account_number_last4?: string;
  opening_balance?: number;
}

export interface PaymentProfileUpsertRequest {
  user_ref: string;
  provider: string;
  profile_name: string;
  linked_account_name: string;
}

export async function getAccounts(token: string) {
  const data = await getDashboard("monthly", token);
  return data.accounts;
}

export async function getPaymentProfiles(userRef: string, token: string) {
  return apiFetch<PaymentProfilesResponse>(
    `/api/v1/ledger/payment-profiles/${userRef}`,
    { token }
  );
}

export async function createAccount(request: AccountUpsertRequest, token: string) {
  return apiFetch<{ status: string; result: any }>(
    `/api/v1/ledger/accounts`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      token,
    }
  );
}

export async function linkPaymentProfile(request: PaymentProfileUpsertRequest, token: string) {
  return apiFetch<{ status: string; result: any }>(
    `/api/v1/ledger/payment-profiles`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      token,
    }
  );
}
