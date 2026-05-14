# Category Colors Fix - Complete

## Issue
The spending by category section in the reports page was not properly assigning colors to each category. All categories were showing in gray because the `categoryColor()` function only had colors for transaction **types** (expense, income, transfer) but was being used for spending **categories** (food, shopping, travel, etc.).

## Solution
Added comprehensive `CATEGORY_COLORS` mapping in `web/src/lib/format.ts` with distinct colors for each category that the NLP model can predict.

## NLP Model Categories
The NLP model (`src/nlp/inference.py`) predicts these 10 categories:
1. **education** - Cyan (#06b6d4)
2. **emi** - Red (#ef4444) - EMI/loan payments
3. **entertainment** - Purple (#8b5cf6)
4. **food** - Amber (#f59e0b)
5. **friends** - Orange (#f97316) - Social spending
6. **healthcare** - Emerald (#10b981)
7. **investment** - Purple (#8b5cf6)
8. **shopping** - Pink (#ec4899)
9. **travel** - Blue (#3b82f6)
10. **utilities** - Gray (#6b7280)

## Additional Category Aliases
Also added color mappings for common category aliases:
- dining, restaurant, groceries (food-related)
- retail, clothing (shopping-related)
- transport, fuel (travel-related)
- bills, electricity, water (utilities-related)
- health, fitness, medical (healthcare-related)
- savings (investment-related)
- social (friends-related)
- books (education-related)

## Implementation Details

### Color Assignment Logic
The `categoryColor()` function now follows this priority:
1. **Category colors** - Check `CATEGORY_COLORS` first (e.g., "food" → amber)
2. **Type colors** - Fallback to `TYPE_COLORS` (e.g., "expense" → red)
3. **Hash-based fallback** - Generate consistent color for unknown categories

### Hash-Based Fallback
For any unknown categories not in the mapping, the function generates a consistent color based on the category name's hash. This ensures:
- Same category always gets the same color
- New categories automatically get distinct colors
- No gray "unknown" categories

## Files Modified
- `web/src/lib/format.ts` - Added comprehensive category color mappings

## Result
✅ Each spending category now has a distinct, vibrant color in the pie chart
✅ All NLP model categories are covered
✅ Common category aliases are supported
✅ Unknown categories get consistent hash-based colors
✅ No more gray categories in the reports page

## Testing
To verify the fix:
1. Navigate to the Reports page (`/reports`)
2. Check the "Spending by Category" pie chart
3. Each category should have a distinct color:
   - Food/Dining: Amber
   - Shopping: Pink
   - Travel: Blue
   - Entertainment: Purple
   - Healthcare: Emerald
   - Friends: Orange
   - Education: Cyan
   - Utilities: Gray
   - EMI: Red
   - Investment: Purple

## Git Commits
1. `9191542` - Fix category colors in reports page - add distinct colors for each spending category
2. `3b86400` - Add missing category colors for emi and healthcare
