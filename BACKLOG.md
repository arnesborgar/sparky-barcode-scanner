# Pi Scanner Backlog

## Usage
- Move tickets between sections as work progresses.
- Keep ticket IDs stable for references in commits/PRs.
- Update `Owner`, `Target`, and `Notes` as needed.

## Todo

### T-001 Adaptive Weekly Coach
- Size: `M`
- Priority: `P1`
- Owner: `unassigned`
- Target: `Week 5`
- Summary:
- Build weekly AI coaching summary from last 7 days across nutrition, sleep, mood, workouts, and adherence.
- Acceptance criteria:
- Weekly summary schema is stable and includes rationale.
- Recommendations are small and realistic (3-5 actions).
- Handles sparse-data days gracefully.
- Dependencies:
- Week 1 dashboard nutrient/goals payload
- Daily aggregation contract

### T-002 Smart Meal Swaps
- Size: `S`
- Priority: `P1`
- Owner: `unassigned`
- Target: `Week 4`
- Summary:
- Suggest 3 equivalent food swaps matching calories/macros with optional sodium/sugar/fiber constraints.
- Acceptance criteria:
- Returns exactly 3 ranked swaps with comparison payload.
- One-click replace updates diary entry and totals.
- Outlier safeguards prevent extreme mismatches.
- Dependencies:
- Existing AI food generation flow
- Diary mutation endpoint

### T-003 MCP Coach Actions + Dry Run
- Size: `L`
- Priority: `P2`
- Owner: `unassigned`
- Target: `Week 6`
- Summary:
- Add safe MCP actions with dry-run preview and explicit confirm/commit behavior.
- Actions:
- `log_food_entry`
- `set_weekly_goal`
- `copy_meal_to_date`
- Acceptance criteria:
- Dry-run and commit paths exist for each action.
- Every commit returns explainability: what changed, why, how to undo.
- Audit records are persisted for all committed changes.
- Dependencies:
- MCP action router
- Audit logging model
- Action authorization guardrails

### T-004 Micronutrient Dashboard v1
- Size: `M`
- Priority: `P0`
- Owner: `unassigned`
- Target: `Week 1`
- Summary:
- Extend `/api/dashboard/stats` with `nutrients` and `goals` for selected nutrients.
- Add preference-driven nutrient cards to dashboard/diary top area.
- Acceptance criteria:
- Endpoint includes selected nutrients and goal values.
- UI cards respect user nutrient preferences.
- No duplicated aggregation logic.

### T-005 Micronutrient Completeness + Data Quality
- Size: `M`
- Priority: `P0`
- Owner: `unassigned`
- Target: `Week 2`
- Summary:
- Normalize extra vitamin/mineral mappings into `custom_nutrients`.
- Add confidence flags and unknown-vs-zero handling.
- Acceptance criteria:
- Provider normalization map is implemented.
- Confidence metadata exposed to UI.
- UI clearly distinguishes unknown from zero.

### T-006 Azure OpenAI First-Class Support
- Size: `M`
- Priority: `P0`
- Owner: `unassigned`
- Target: `Week 3`
- Summary:
- Add `azure_openai` service type with deployment-based endpoint support and Azure auth header mode.
- Acceptance criteria:
- Service config supports deployment + api-version.
- Backward compatibility with `openai_compatible` retained.
- Settings UI supports Azure-specific fields.

### T-007 Weekly Adaptive Coach UX
- Size: `S`
- Priority: `P1`
- Owner: `unassigned`
- Target: `Week 5`
- Summary:
- Reports surface for weekly coaching recommendations and apply/select actions.
- Acceptance criteria:
- User can apply all or selected recommendations.
- Changes are visible and traceable in UI.

### T-008 Mapping Validation Harness
- Size: `S`
- Priority: `P1`
- Owner: `unassigned`
- Target: `Pre-Week 2`
- Summary:
- Add validation mode to show source used and nutrient key counts.
- Acceptance criteria:
- Structured logs report source and key coverage.
- No runtime errors in validation mode.

### T-009 Unit + Integration Tests
- Size: `M`
- Priority: `P1`
- Owner: `unassigned`
- Target: `Pre-Week 3`
- Summary:
- Add test coverage for OFF/estimated/USDA mapping, `net_carbs`, and review-flag behavior.
- Acceptance criteria:
- Deterministic tests pass for key mapping paths.
- Regression test catches source fallback failures.

## In Progress
- None.

## Blocked
- None.

## Done

### D-001 USDA Extended Custom Nutrient Mapping
- Completed:
- Extended USDA enrichment into `custom_nutrients` in scanner and app mapping paths.
- Added `net_carbs` computation.
- README updated to document custom nutrient keys.

### D-002 GitHub Repo Hygiene and Metadata Updates
- Completed:
- Updated About descriptions on requested repositories.
- Cleaned and validated `jvverd` reference removal on targeted repos where applicable.
