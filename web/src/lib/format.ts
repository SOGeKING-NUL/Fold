export function formatINR(minor: number): string {
  const rupees = minor / 100;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(rupees);
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Consistent color scheme based on transaction type
const TYPE_COLORS: Record<string, string> = {
  expense: "#ef4444",      // red for expenses
  income: "#22c55e",       // green for income
  transfer: "#3b82f6",     // blue for transfers
  investment: "#8b5cf6",   // purple for investments
  opening_balance: "#6b7280", // gray for opening balance
};

export function categoryColor(key: string | null | undefined): string {
  if (!key) return "#6b7280";
  return TYPE_COLORS[key.toLowerCase()] || "#6b7280";
}

export function capitalize(s: string): string {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ");
}
