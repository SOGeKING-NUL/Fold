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

const CATEGORY_COLORS: Record<string, string> = {
  food: "#f97316",
  shopping: "#8b5cf6",
  travel: "#06b6d4",
  entertainment: "#ec4899",
  utilities: "#84cc16",
  healthcare: "#ef4444",
  education: "#3b82f6",
  emi: "#f59e0b",
  investment: "#10b981",
  friends: "#a855f7",
  misc: "#6b7280",
  uncategorized: "#9ca3af",
  expense: "#6b7280",
  income: "#22c55e",
};

export function categoryColor(key: string): string {
  return CATEGORY_COLORS[key.toLowerCase()] || "#6b7280";
}

export function capitalize(s: string): string {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ");
}
