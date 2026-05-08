# Demo Queries

## Recommended Demo Order
1. Product workflow query
2. API query
3. Diagnostics showcase query
4. Hybrid retrieval query
5. HR query
6. Insufficient-context safety query

## API Queries
- "How does JWT authentication work in this API platform?"
- "Which endpoint controls knowledge base access assignment?"
- Expected behavior: API-oriented answer, API source cards.
- Expected providers: OpenAI recommended for stable demo.
- Fallback expectation: Should not fallback for covered API docs.

## Product Workflow Queries
- "What is Claims Portal and what workflow does it support?"
- "Summarize the main user flow for submitting a claim."
- Expected behavior: Product-focused response with product/source metadata.
- Expected providers: OpenAI recommended; Ollama may degrade intermittently.

## HR Queries
- "What details are captured for HR resume screening?"
- "What HR document sections are considered during retrieval?"
- Expected behavior: HR KB-scoped response only for HR user/admin context.

## Insufficient-context Safety Query
- "Explain the quantum wormhole banana protocol in our platform."
- Expected behavior: safe fallback response and insufficient-context banner.
- Fallback expectation: `llm_status=fallback_insufficient_context`.

## Hybrid Retrieval Query
- "Compare authentication and KB access controls in one summary."
- Expected behavior: retrieval diagnostics may show hybrid rescue/fusion fields when relevant.

## Diagnostics Showcase Query
- "List the current retrieval mode and provider details for this answer."
- Expected behavior: diagnostics panel shows provider/retrieval/fallback fields for admin/QA only.
