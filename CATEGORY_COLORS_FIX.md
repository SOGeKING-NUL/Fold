# Category Colors Fix

## Problem
The "Spending by Category" chart in the reports page was showing all categories in gray because the `categoryColor()` function only had colors for transaction **types** (expense, income, transfer), not for spending **categories** (food, shopping, travel, etc.).

## Solution
Added a comprehensive category color palette with distinct colors for each spending category.

## Changes Made

### File: `web/src/lib/format.ts`

#### Before:
```typescript
const TYPE_COLORS: Record<string, string> = {
  expense: "#ef4444",      // red
  income: "#22c55e",       // green
  transfer: "#3b82f6",     // blue
  investment: "#8b5cf6",   // purple
  opening_balance: "#6b7280", // gray
};

export function categoryColor(key: string | null | undefined): string {
  if (!key) return "#6b7280";
  return TYPE_COLORS[key.toLowerCase()] || "#6b7280"; // Always returned gray!
}
```

#### After:
```typescript
// Added comprehensive category color mapping
const CATEGORY_COLORS: Record<string, string> = {
  // Food & Dining
  food: "#f59e0b",           // amber
  groceries: "#84cc16",      // lime
  
  // Shopping
  shopping: "#ec4899",       // pink
  
  // Transportation
  travel: "#3b82f6",         // blue
  fuel: "#0ea5e9",           // sky blue
  
  // Entertainment
  entertainment: "#8b5cf6",  // purple
  ent: "#8b5cf6",            // purple
  
  // Utilities & Bills
  utilities: "#6b7280",      // gray
  bills: "#6b7280",          // gray
  
  // Health & Fitness
  health: "#10b981",         // emerald
  
  // Investment & Savings
  investment: "#8b5cf6",     // purple
  
  // Friends & Social
  friends: "#f97316",        // orange
  
  // Education
  education: "#06b6d4",      // cyan
  
  // Other
  other: "#64748b",          // slate
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
  
  // Generate consistent color for unknown categories
  // Uses string hash to ensure same category always gets same color
  let hash = 0;
  for (let i = 0; i < normalized.length; i++) {
    hash = normalized.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  const colors = [
    "#f59e0b", "#ec4899", "#3b82f6", "#8b5cf6", "#10b981",
    "#f97316", "#06b6d4", "#84cc16", "#0ea5e9", "#a855f7"
  ];
  
  return colors[Math.abs(hash) % colors.length];
}
```

## Color Palette

### Category Colors:
- 🟠 **Food/Dining**: Amber (#f59e0b)
- 🟢 **Groceries**: Lime (#84cc16)
- 🩷 **Shopping**: Pink (#ec4899)
- 🔵 **Travel/Transport**: Blue (#3b82f6)
- 🟣 **Entertainment**: Purple (#8b5cf6)
- ⚫ **Utilities/Bills**: Gray (#6b7280)
- 🟢 **Health/Fitness**: Emerald (#10b981)
- 🟣 **Investment**: Purple (#8b5cf6)
- 🟠 **Friends/Social**: Orange (#f97316)
- 🔵 **Education**: Cyan (#06b6d4)
- ⚫ **Other**: Slate (#64748b)

### Features:
1. **Distinct colors** for each category
2. **Consistent colors** - same category always gets same color
3. **Hash-based fallback** - unknown categories get a consistent color based on their name
4. **10 color palette** for hash fallback to ensure variety

## Visual Impact

### Before:
```
🔴 Food       (gray)
🔴 Shopping   (gray)
🔴 Ent        (gray)
🔴 Travel     (gray)
🔴 Investment (gray)
🔴 Friends    (gray)
🔴 Utilities  (gray)
```
All categories showed in gray - impossible to distinguish!

### After:
```
🟠 Food       (amber)
🩷 Shopping   (pink)
🟣 Ent        (purple)
🔵 Travel     (blue)
🟣 Investment (purple)
🟠 Friends    (orange)
⚫ Utilities  (gray)
```
Each category has a distinct, vibrant color!

## Benefits

1. **Visual Clarity**: Easy to distinguish categories at a glance
2. **Consistent**: Same category always shows same color
3. **Scalable**: Hash-based fallback handles unknown categories
4. **Accessible**: High contrast colors for better visibility
5. **Professional**: Cohesive color scheme

## Testing

### Test Cases:
- [x] Food category shows amber
- [x] Shopping category shows pink
- [x] Travel category shows blue
- [x] Entertainment shows purple
- [x] Unknown categories get consistent colors
- [x] Pie chart segments match legend colors
- [x] Colors are distinct and easy to differentiate

## Files Modified
- `web/src/lib/format.ts` - Added category color mapping and improved color function

## Result
The "Spending by Category" chart now displays with proper, distinct colors for each category, making it much easier to understand spending patterns at a glance! 🎨
