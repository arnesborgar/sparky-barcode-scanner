# Roadmap (No Admin Track, Product + AI + MCP)

## Week 1: Micronutrient Dashboard v1
- Extend `/api/dashboard/stats` to include `nutrients` and `goals` object for selected nutrients.
- Wire to existing nutrition aggregation instead of duplicating logic.
- Add preference-driven nutrient cards to dashboard/diary top area.
- Files: `DashboardService.js`, `dashboardRoutes.js`, `DiaryTopControls.tsx`, `useDailyProgress.ts`.

## Week 2: Micronutrient Completeness + Data Quality
- Add provider normalization map for extra vitamins/minerals into `custom_nutrients` when not in core columns.
- Add confidence flags per nutrient source for missing/estimated values.
- Add `unknown` vs `zero` rendering in UI to avoid misleading zeros.
- Files: `nutritionixService.js`, `tandoorService.js`, `foodUtils.js`, `nutrients.ts`.

## Week 3: Azure OpenAI First-Class Support
- Add explicit `azure_openai` service type end-to-end.
- Build endpoint as `.../openai/deployments/{deployment}/chat/completions?api-version=...`.
- Support Azure auth header mode and deployment name field in settings UI.
- Keep backward compatibility with `openai_compatible`.
- Files: `aiServiceUtils.ts`, `ServiceForm.tsx`, `chatService.js`, `config.js`.

## Week 4: Smart Meal Swaps
- Add AI intent `suggest_swaps` using diary context + nutrient goals.
- Return 3 alternatives preserving calories/macros and optionally sodium/sugar/fiber constraints.
- One-click replace in diary entry UI.
- Files: `chatService.js`, `chatRoutes.js`, `SparkyNutritionCoach.tsx`, `Chatbot_FoodHandler.ts`.

## Week 5: Weekly Adaptive Coach
- Weekly summary job computes adherence and recommends small plan changes.
- Output `next 7 days` suggestions for calories/macros/micros and workout load.
- User can apply all or pick per recommendation.
- Files: `services`, `reportRepository.js`, `Reports`.

## Week 6: MCP Action Layer (Safe Automation)
- Add MCP actions for bounded operations: `log_food_entry`, `set_goal_for_day`, `copy_meal_plan_day`.
- Add dry-run + confirm flow and audit log response for each action.
- Files: `src`, `routes`, `models`.

## Suggested Priority Order
1. Micronutrient Dashboard v1
2. Azure OpenAI first-class support
3. Smart Meal Swaps
4. Weekly Adaptive Coach
5. MCP action layer

## Next Step
Convert this roadmap into a concrete implementation backlog with ticket-sized tasks (`S/M/L`), acceptance criteria, and an exact API contract for the new dashboard nutrient payload.

## Idea Backlog

### High-Impact Ideas

#### Adaptive weekly coach
- AI reviews last 7 days across nutrition, sleep, mood, workouts, and adherence.
- Produces one weekly plan with small, realistic adjustments.
- Uses existing goals + diary + check-in data.

#### What changed? insights engine
- Detect trend breaks automatically: weight plateau, sleep dip, mood drop, protein consistency.
- Explain likely drivers using correlations from user data.
- Surface as plain-language cards in Reports.

#### Smart meal swaps
- In diary, user taps a food and requests 3 equivalent swaps matching calories/macros.
- Pull options from existing food DB/providers.
- Integrates with existing AI food generation flow.

#### Context-aware chatbot memory
- Chatbot references recent logs automatically (for example: fiber adherence trend).
- Add `coach mode` vs `quick logging mode`.
- Build on existing chat history storage with prompt + retrieval updates.

#### Recovery readiness score
- Combine sleep, exercise load, mood/stress, and recent calorie deficit.
- Suggest `push` / `maintain` / `deload` for today.
- Reuses existing collected signals.

### API / Integration Extensions

#### Barcode confidence resolver
- If OpenFoodFacts result is low confidence, auto-fallback to AI extraction from label photo.
- Ask one clarification question when ambiguous.
- Goal: improve real-world logging quality.

#### Multi-source nutrition reconciliation
- If provider values differ materially, show a `best estimate` with confidence badge.
- Allow preferred source selection globally or by food type.

#### Wearable data normalization layer
- Build one `daily metrics contract` to unify Garmin/mobile/manual entries.
- Goal: improve downstream AI analysis and reduce edge-case handling.

### MCP-Powered Features

#### Coach tools via MCP actions
- Expose safe MCP actions such as:
- `log_food_entry`
- `create_meal_plan_template`
- `set_weekly_goal`
- `copy_meal_to_date`
- Goal: bounded, auditable AI actions instead of chat-only guidance.

#### Explainable AI actions
- Every MCP action returns:
- what changed
- why it was suggested
- how to undo
- Goal: increase trust and reduce accidental edits.

#### Dry-run planning mode
- AI proposes a 7-day plan via MCP preview objects.
- User approves, then MCP commits changes.
- Goal: safer automation with explicit confirmation.

## Backlog Note
- These ideas are intentionally not scheduled by week yet.
- They should be prioritized after Week 1-6 execution based on impact, implementation risk, and data readiness.

## Top 3 Draft Tickets

### T-001 Adaptive Weekly Coach (M)
- Size: `M`
- Priority: `P1`
- Source idea: `Adaptive weekly coach`
- Goal:
- Generate one weekly coaching plan using last 7 days of nutrition, sleep, mood, workouts, and adherence.
- Scope:
- Build a weekly aggregation job/service.
- Compute deltas versus user goals and recent baseline.
- Produce 3-5 small actionable recommendations for next week.
- Persist summary output for UI retrieval.
- Dependencies:
- Week 1 nutrient/goals payload available in dashboard/report paths.
- Reliable daily data aggregation contract (nutrition + sleep + mood + workouts).
- Initial recommendation prompt template and response schema.
- Definition of done:
- Weekly summary endpoint/service returns deterministic JSON schema.
- Recommendations include rationale and target metric.
- At least one integration test covers sparse-data and complete-data scenarios.
- UI can render summary and recommendations without manual transformation.

### T-002 Smart Meal Swaps (S)
- Size: `S`
- Priority: `P1`
- Source idea: `Smart meal swaps`
- Goal:
- From a selected diary food, return 3 equivalent swaps matching calories/macros with optional sodium/sugar/fiber constraints.
- Scope:
- Add `suggest_swaps` intent in chat/coach flow.
- Retrieve candidate foods from local DB + configured providers.
- Rank candidates by macro distance and selected nutrient constraints.
- Add one-click replace action in diary UI.
- Dependencies:
- Existing AI food generation/selection flow.
- Access to diary meal context and current goal constraints.
- Food replacement mutation endpoint in diary flow.
- Definition of done:
- Given a diary item, API returns exactly 3 ranked swaps with comparison payload.
- One-click replace updates diary entry and recalculates daily totals.
- Validation prevents extreme outliers (for example 10x calories mismatch).
- Basic analytics/logging captures accepted vs rejected swaps.

### T-003 Coach MCP Actions + Dry Run (L)
- Size: `L`
- Priority: `P2`
- Source ideas: `Coach tools via MCP actions`, `Explainable AI actions`, `Dry-run planning mode`
- Goal:
- Enable safe, auditable MCP-powered coaching actions with preview/confirm workflow.
- Scope:
- Implement bounded MCP actions:
- `log_food_entry`
- `set_weekly_goal`
- `copy_meal_to_date`
- Add dry-run response format with `proposed_changes`.
- Add confirm endpoint/flag to commit dry-run proposals.
- Return explainability block on every action:
- `what_changed`
- `why_suggested`
- `how_to_undo`
- Dependencies:
- MCP action router scaffold.
- Auditable change log model/table.
- Authorization and guardrails for write actions.
- Definition of done:
- Each action supports both dry-run and commit paths.
- All committed actions emit audit records with user, timestamp, payload, and undo hints.
- Unauthorized or out-of-bounds actions are blocked with explicit error reasons.
- End-to-end test covers preview -> confirm -> undo guidance chain.
