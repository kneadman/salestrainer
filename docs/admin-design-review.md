# Admin Design Review

> Date: 2026-05-19
> Method: code-based audit (admin.css + all admin components)
> Scope: /admin routes — Dashboard, Organizations, OrganizationDetail, History, AuditLog, UserAnalytics

## Checklist

| Area | Status | Notes |
|------|--------|-------|
| Colors | ⚠️ | Mint accent unified, but badge/tag colors still blue-tinted |
| Typography | ✅ | Consistent with client cabinet |
| Spacing | ⚠️ | Mobile breakpoint differs from client (860px vs 760px) |
| Responsive | ❌ | Admin tables have no mobile adaptation |
| Accessibility | ⚠️ | Buttons used for navigation inside pages (same as #8) |
| AI slop | ✅ | No obvious generated-code artifacts |

## Findings

### High

1. **Admin table overflow on mobile**
   - `.admin-table` has `min-width: 760px` and no mobile media query override.
   - Affected pages: Organizations, History, AuditLog, UserAnalytics.
   - Same root cause as client-table (#5), but admin.css was missed.

2. **Admin nav truncation on mobile**
   - `.admin-nav` on `@media (max-width: 860px)` uses `grid-template-columns: repeat(auto-fit, minmax(150px, 1fr))`.
   - Long labels like "История тренировок" overflow or force multi-line rows.
   - No horizontal scroll or fade hint (unlike client-nav after #6).

3. **Navigation buttons inside admin pages**
   - HistoryTable, HistoryDetail, OrganizationDetailPage, UserAnalyticsPage use `<button onClick={() => onNavigate(...)}>`.
   - Same issue as #8: middle-click / Ctrl+Click / right-click "Open in new tab" broken.

### Medium

4. **Inconsistent mobile breakpoint**
   - Client: 760px. Admin: 860px. Causes divergent responsive behavior.

5. **Admin tabs wrap awkwardly on mobile**
   - OrganizationDetailPage has 6 tabs. `.admin-tabs` flex-wraps but tabs don't shrink.
   - On 375px they occupy 2–3 rows, pushing content far down.

6. **Missing overflow-wrap in admin-table cells**
   - `.admin-table td` lacks `overflow-wrap: anywhere`, worsening overflow when `min-width` is reduced.

7. **Tag chip color inconsistency**
   - `.tag-chip` uses `rgba(125, 242, 196, ...)` = `#7df2c4`, not the unified mint `#5eead4`.

8. **Admin badge text color blue-tinted**
   - `.admin-badge` uses `#dbeafe` (blue-tinted white). Should use mint or neutral text.

### Polish

9. **Admin denied card lacks padding on mobile**
   - `.admin-denied__card` has `width: min(520px, 100%)` but no padding. Text touches edges on narrow screens.

10. **Stat card font size inconsistency**
    - Admin `1.7rem` vs Client `1.65rem`. Minor mismatch.

11. **Admin page header gap too large on mobile**
    - `gap: 18px` vs client `gap: 12px` on mobile.
