# Demo Script

## Part 1 - Platform introduction
- What to say: "This is an enterprise multi-domain AI knowledge platform with strict RBAC and KB isolation."
- What to click: Login page -> sign in as `superadmin@local`.
- Expected output: Dashboard and all workspaces become visible.
- Backup path: If login fails, verify backend health and retry with seeded admin.

## Part 2 - RBAC and KB isolation
- What to say: "Visibility and actions are driven by role + KB access, never by frontend assumptions."
- What to click: KB selector, sidebar sections, then switch account to `hr@local`.
- Expected output: HR user sees only HR KB scope; admin/diagnostics hidden.
- Backup path: If scope looks wrong, check `/knowledge-bases/me` response.

## Part 3 - API workspace demo
- What to say: "API workspace supports KB-scoped answers and source traceability."
- What to click: Select API KB -> Chat -> ask API query from demo sheet.
- Expected output: Answer card, source cards, diagnostics (admin/QA only).
- Backup path: If weak retrieval, ask alternate API query from demo sheet.

## Part 4 - Product workspace demo
- What to say: "Product workflows use product metadata and section-aware retrieval context."
- What to click: Select Product KB -> ask product workflow question.
- Expected output: Product-aligned answer with product/source metadata.
- Backup path: If answer weak, use stable product query with known source coverage.

## Part 5 - Document upload demo
- What to say: "Upload is permission-aware and always KB-scoped."
- What to click: Documents page -> upload in admin/write user context.
- Expected output: Upload result card and refreshed document list.
- Backup path: If parser issue occurs, show existing document list and explain enforced validation.

## Part 6 - Diagnostics/transparency demo
- What to say: "Diagnostics provide provider/retrieval visibility for admin/QA transparency."
- What to click: Toggle diagnostics panel as `superadmin@local` or `qa@local`.
- Expected output: Provider, retrieval, fallback fields visible.
- Backup path: If empty, run one new query to refresh latest diagnostics.

## Part 7 - Insufficient-context safety demo
- What to say: "When context is insufficient, the platform returns a safe deterministic fallback."
- What to click: Ask insufficient-context query from demo sheet.
- Expected output: `fallback_insufficient_context` behavior and safety banner.
- Backup path: If not triggered, use a more out-of-domain query.

## Part 8 - Provider abstraction demo
- What to say: "Provider mode is config-driven; no frontend/backend redesign needed."
- What to click: Show provider badge and diagnostics provider fields.
- Expected output: Provider markers match backend mode.
- Backup path: If mismatch, restart backend with explicit provider env values.

## Part 9 - HR workspace demo
- What to say: "HR users are isolated to HR domain access."
- What to click: Login as `hr@local` -> open KB selector and chat/documents.
- Expected output: HR-only KB visibility, no admin/diagnostics controls.
- Backup path: If HR access missing, re-run user seed script.

## Part 10 - Future roadmap
- What to say: "Recruitment, analytics, and advanced diagnostics are visible as controlled future-phase placeholders."
- What to click: Dashboard placeholder cards.
- Expected output: Placeholder cards marked Future Phase.
- Backup path: If not visible, explain placeholders are role/context dependent.
