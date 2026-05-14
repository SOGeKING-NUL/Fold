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

// Category color palette - distinct colors for each spending category
const CATEGORY_COLORS: Record<string, string> = {
  // Food & Dining
  food: "#f59e0b",           // amber
  dining: "#f59e0b",         // amber
  restaurant: "#f59e0b",     // amber
  groceries: "#84cc16",      // lime
  
  // Shopping
  shopping: "#ec4899",       // pink
  retail: "#ec4899",         // pink
  clothing: "#ec4899",       // pink
  
  // Transportation
  travel: "#3b82f6",         // blue
  transport: "#3b82f6",      // blue
  fuel: "#0ea5e9",           // sky blue
  
  // Entertainment
  entertainment: "#8b5cf6",  // purple
  ent: "#8b5cf6",            // purple (short form)
  movies: "#8b5cf6",         // purple
  games: "#a855f7",          // purple-500
  
  // Utilities & Bills
  utilities: "#6b7280",      // gray
  bills: "#6b7280",          // gray
  electricity: "#6b7280",    // gray
  water: "#6b7280",          // gray
  
  // Health & Fitness
  health: "#10b981",         // emerald
  healthcare: "#10b981",     // emerald
  fitness: "#10b981",        // emerald
  medical: "#10b981",        // emerald
  
  // Investment & Savings
  investment: "#8b5cf6",     // purple
  savings: "#8b5cf6",        // purple
  emi: "#ef4444",            // red (EMI/loan payments)
  
  // Friends & Social
  friends: "#f97316",        // orange
  social: "#f97316",         // orange
  
  // Education
  education: "#06b6d4",      // cyan
  books: "#06b6d4",          // cyan
  
  // Other
  other: "#64748b",          // slate
  miscellaneous: "#64748b",  // slate
  expense: "#ef4444",        // red (fallback)
};

export function categoryColor(key: string | null | undefined): string {
  if (!key) return "#6b7280";
  const normalized = key.toLowerCase().trim();
  
  // Check category colors first
  if (CATEGORY_COLORS[normalized]) {
    return CATEGORY_COLORS[normalized];
  }
  
  // Fallback to type colors
  if (TYPE_COLORS[normalized]) {
    return TYPE_COLORS[normalized];
  }
  
  // Generate a consistent color based on the string hash for unknown categories
  let hash = 0;
  for (let i = 0; i < normalized.length; i++) {
    hash = normalized.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  const colors = [
    "#f59e0b", // amber
    "#ec4899", // pink
    "#3b82f6", // blue
    "#8b5cf6", // purple
    "#10b981", // emerald
    "#f97316", // orange
    "#06b6d4", // cyan
    "#84cc16", // lime
    "#0ea5e9", // sky
    "#a855f7", // purple-500
  ];
  
  return colors[Math.abs(hash) % colors.length];
}

export function capitalize(s: string): string {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ");
}
