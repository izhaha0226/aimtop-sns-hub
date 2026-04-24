# Multi-LLM Engine + 8-Channel Benchmarking Implementation Plan

> For Hermes: Use subagent-driven-development skill to implement this plan task-by-task.

Goal: Add a switchable Claude/GPT engine, UI-configurable K-value benchmarking controls, and an 8-channel benchmark intelligence pipeline that feeds SNS strategy and content generation.

Architecture: Introduce a backend LLM router layer that abstracts Claude and GPT behind one interface, then add benchmark collection/scoring/profile services that produce reusable action-language profiles. Expose both through admin-configurable settings pages and content-generation APIs so the frontend can select engines and benchmark intensity without code changes.

Tech Stack: FastAPI, async SQLAlchemy, Pydantic v2, Next.js 15, TypeScript, existing admin secrets/settings UI, existing AI/growth/content services.

---

## Task 1: Add database models for LLM routing and benchmark intelligence

Objective: Create the minimum schema needed to persist provider configs, task policies, benchmark accounts/posts, and action-language profiles.

Files:
- Create: `backend/models/llm_provider_config.py`
- Create: `backend/models/llm_task_policy.py`
- Create: `backend/models/benchmark_account.py`
- Create: `backend/models/benchmark_post.py`
- Create: `backend/models/action_language_profile.py`
- Modify: `backend/models/__init__.py`
- Test: `backend/tests/test_llm_benchmark_models.py`

Step 1: Write failing model metadata test

```python
from models import Base


def test_llm_and_benchmark_tables_registered():
    names = set(Base.metadata.tables.keys())
    assert "llm_provider_configs" in names
    assert "llm_task_policies" in names
    assert "benchmark_accounts" in names
    assert "benchmark_posts" in names
    assert "action_language_profiles" in names
```

Step 2: Run test to verify failure

Run: `cd backend && source .venv/bin/activate && pytest tests/test_llm_benchmark_models.py -v`
Expected: FAIL — missing model/table registrations.

Step 3: Write minimal models

Key fields to include:

```python
# llm_provider_configs
id, provider_name, model_name, label, is_active, is_default,
supports_json, supports_reasoning, timeout_seconds, max_tokens,
created_at, updated_at

# llm_task_policies
task_type, routing_mode, primary_provider, primary_model,
fallback_provider, fallback_model, top_k,
views_weight, engagement_weight, recency_weight, action_language_weight,
benchmark_window_days, strict_json_mode, is_active

# benchmark_accounts
client_id, platform, handle, source_type, purpose,
is_active, auto_discovered, metadata_json

# benchmark_posts
benchmark_account_id, client_id, platform, external_post_id, post_url,
content_text, hook_text, cta_text, hashtags_json, format_type,
view_count, like_count, comment_count, share_count, save_count,
engagement_rate, benchmark_score, published_at, raw_payload

# action_language_profiles
client_id, platform, source_scope, top_hooks_json, top_ctas_json,
tone_patterns_json, format_patterns_json, recommended_prompt_rules,
profile_version
```

Step 4: Register imports in `backend/models/__init__.py`

Example pattern:

```python
from .llm_provider_config import LLMProviderConfig
from .llm_task_policy import LLMTaskPolicy
from .benchmark_account import BenchmarkAccount
from .benchmark_post import BenchmarkPost
from .action_language_profile import ActionLanguageProfile
```

Step 5: Run test to verify pass

Run: `cd backend && source .venv/bin/activate && pytest tests/test_llm_benchmark_models.py -v`
Expected: PASS

Step 6: Commit

```bash
git add backend/models backend/tests/test_llm_benchmark_models.py
git commit -m "feat: add llm routing and benchmark intelligence models"
```

---

## Task 2: Add migration for new tables

Objective: Persist the new model layer safely in PostgreSQL.

Files:
- Create: `backend/alembic/versions/006_add_llm_and_benchmark_tables.py`
- Test: `backend/tests/test_alembic_llm_benchmark_upgrade.py`

Step 1: Write failing migration smoke test

```python
def test_upgrade_head_includes_llm_and_benchmark_tables():
    # Use temporary database or migration test harness
    assert False, "migration not added yet"
```

Step 2: Run test to verify failure

Run: `cd backend && source .venv/bin/activate && pytest tests/test_alembic_llm_benchmark_upgrade.py -v`
Expected: FAIL

Step 3: Create Alembic revision

Include create_table statements for:
- `llm_provider_configs`
- `llm_task_policies`
- `benchmark_accounts`
- `benchmark_posts`
- `action_language_profiles`

Add useful indexes:
- `benchmark_posts(platform, client_id, benchmark_score)`
- `benchmark_posts(benchmark_account_id, published_at)`
- `llm_task_policies(task_type)` unique

Step 4: Run migration locally

Run:
`cd backend && source .venv/bin/activate && alembic upgrade head`
Expected: success with no SQL errors.

Step 5: Run test to verify pass

Run: `cd backend && source .venv/bin/activate && pytest tests/test_alembic_llm_benchmark_upgrade.py -v`
Expected: PASS

Step 6: Commit

```bash
git add backend/alembic/versions/006_add_llm_and_benchmark_tables.py backend/tests/test_alembic_llm_benchmark_upgrade.py
git commit -m "feat: add migration for llm routing and benchmark tables"
```

---

## Task 3: Create backend LLM router abstraction

Objective: Remove direct Claude-only coupling from the application layer.

Files:
- Create: `backend/services/llm/base.py`
- Create: `backend/services/llm/claude_engine.py`
- Create: `backend/services/llm/gpt_engine.py`
- Create: `backend/services/llm/router.py`
- Modify: `backend/services/ai_service.py`
- Test: `backend/tests/test_llm_router.py`

Step 1: Write failing router test

```python
import pytest
from services.llm.router import LLMRouter


@pytest.mark.asyncio
async def test_router_resolves_primary_engine(monkeypatch):
    router = LLMRouter()
    result = await router.generate_text(
        task_type="copy_generation",
        prompt="hello",
        context={},
        override={"provider": "claude", "model": "claude-sonnet"},
    )
    assert result.provider == "claude"
```

Step 2: Run test to verify failure

Run: `cd backend && source .venv/bin/activate && pytest tests/test_llm_router.py -v`
Expected: FAIL — router missing.

Step 3: Create shared response object and interfaces

Minimal interface:

```python
class LLMGenerationResult(BaseModel):
    provider: str
    model: str
    output_text: str
    parsed_json: dict | list | None = None
    latency_ms: int | None = None

class BaseLLMEngine(Protocol):
    async def generate_text(self, prompt: str, **kwargs) -> LLMGenerationResult: ...
    async def generate_json(self, prompt: str, **kwargs) -> LLMGenerationResult: ...
```

Step 4: Implement Claude engine wrapper

Use existing CLI call path from `ai_service.py`.
Do not remove `call_claude()` immediately; refactor it to call the new Claude engine internally.

Step 5: Implement GPT engine wrapper

Important constraint:
- Do not hardcode API keys in code.
- Read runtime values through settings/runtime config only.
- If credentials are absent, raise a controlled configuration error.

Minimal first version may use provider configuration plus secret settings like:
- `openai_api_key`
- `openai_base_url` (optional)

Step 6: Implement router logic

Rules:
- explicit override wins
- task policy next
- default provider config last
- fallback engine only on timeout / provider error / parse failure when enabled

Step 7: Run test to verify pass

Run: `cd backend && source .venv/bin/activate && pytest tests/test_llm_router.py -v`
Expected: PASS

Step 8: Commit

```bash
git add backend/services/llm backend/services/ai_service.py backend/tests/test_llm_router.py
git commit -m "feat: add switchable claude gpt llm router"
```

---

## Task 4: Extend runtime settings catalog for LLM engine configuration

Objective: Make provider secrets and engine defaults configurable from UI.

Files:
- Modify: `backend/services/runtime_settings.py`
- Modify: `backend/routes/admin_secrets.py` (only if response fields must expand)
- Create: `backend/schemas/llm_settings.py`
- Create: `backend/routes/admin_ai_settings.py`
- Test: `backend/tests/test_admin_ai_settings.py`

Step 1: Write failing API test

```python
def test_admin_ai_settings_list_returns_task_policies(client, admin_token):
    res = client.get("/api/v1/admin/ai-settings", headers=admin_token)
    assert res.status_code == 200
```

Step 2: Run test to verify failure

Run: `cd backend && source .venv/bin/activate && pytest tests/test_admin_ai_settings.py -v`
Expected: FAIL

Step 3: Extend secret catalog

Add keys such as:
- `openai_api_key`
- `openai_base_url`
- `default_llm_provider`
- `default_llm_model`

Do not mix task policy rows into `app_secret`; keep task policy in its own table.

Step 4: Create admin AI settings routes

Endpoints:
- `GET /api/v1/admin/ai-settings/providers`
- `PUT /api/v1/admin/ai-settings/providers/{id}`
- `GET /api/v1/admin/ai-settings/task-policies`
- `PUT /api/v1/admin/ai-settings/task-policies/{task_type}`

Step 5: Seed minimal defaults in route/service layer when DB empty

Recommended defaults:
- `strategy` → claude / Sonnet
- `benchmark_analysis` → claude / Sonnet
- `copy_generation` → gpt or cheaper model if configured, else claude
- `report_summary` → claude

Step 6: Run test to verify pass

Run: `cd backend && source .venv/bin/activate && pytest tests/test_admin_ai_settings.py -v`
Expected: PASS

Step 7: Commit

```bash
git add backend/services/runtime_settings.py backend/routes/admin_ai_settings.py backend/schemas/llm_settings.py backend/tests/test_admin_ai_settings.py
git commit -m "feat: add admin ai engine settings api"
```

---

## Task 5: Add benchmark scoring and action-language analysis services

Objective: Turn raw benchmark posts into top-K reusable intelligence.

Files:
- Create: `backend/services/benchmark_scoring_service.py`
- Create: `backend/services/action_language_service.py`
- Test: `backend/tests/test_benchmark_scoring_service.py`
- Test: `backend/tests/test_action_language_service.py`

Step 1: Write failing scoring test

```python
def test_score_prefers_high_views_and_engagement():
    post_a = {"view_count": 10000, "engagement_rate": 8.0, "published_at_days_ago": 2, "action_language_score": 0.7}
    post_b = {"view_count": 3000, "engagement_rate": 2.0, "published_at_days_ago": 2, "action_language_score": 0.7}
    assert score(post_a) > score(post_b)
```

Step 2: Write failing action-language test

```python
def test_extracts_hook_and_cta_patterns():
    posts = [
        {"content_text": "지금 안 보면 손해입니다. 저장해두세요"},
        {"content_text": "단 3가지만 체크하세요. 댓글로 알려주세요"},
    ]
    profile = build_action_language_profile("instagram", posts)
    assert profile["top_ctas"]
    assert profile["top_hooks"]
```

Step 3: Run tests to verify failure

Run: `cd backend && source .venv/bin/activate && pytest tests/test_benchmark_scoring_service.py tests/test_action_language_service.py -v`
Expected: FAIL

Step 4: Implement scoring service

Core function:

```python
def calculate_benchmark_score(post, weights):
    return (
        weights.views_weight * normalize_views(post.view_count)
        + weights.engagement_weight * normalize_engagement(post.engagement_rate)
        + weights.recency_weight * normalize_recency(post.published_at)
        + weights.action_language_weight * (post.action_language_score or 0)
    )
```

Step 5: Implement action-language service

Extract at minimum:
- first-line hook
- CTA matches using rule dictionary
- emoji density
- linebreak density
- hashtag count
- sentence length profile

Do not make this fully AI-dependent yet; deterministic extraction first, LLM summarization second.

Step 6: Run tests to verify pass

Run: `cd backend && source .venv/bin/activate && pytest tests/test_benchmark_scoring_service.py tests/test_action_language_service.py -v`
Expected: PASS

Step 7: Commit

```bash
git add backend/services/benchmark_scoring_service.py backend/services/action_language_service.py backend/tests/test_benchmark_scoring_service.py backend/tests/test_action_language_service.py
git commit -m "feat: add benchmark scoring and action language analysis"
```

---

## Task 6: Add benchmark collector API and service skeleton for 8 channels

Objective: Provide one benchmark ingestion surface even though channel capabilities differ.

Files:
- Create: `backend/services/benchmark_collector_service.py`
- Create: `backend/routes/benchmarking.py`
- Create: `backend/schemas/benchmarking.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_benchmarking_routes.py`

Step 1: Write failing route test

```python
def test_benchmark_accounts_crud(client, admin_token):
    res = client.post("/api/v1/benchmarking/accounts", json={
        "client_id": "00000000-0000-0000-0000-000000000001",
        "platform": "instagram",
        "handle": "@aimtop_ref",
        "purpose": "all"
    }, headers=admin_token)
    assert res.status_code == 200
```

Step 2: Run test to verify failure

Run: `cd backend && source .venv/bin/activate && pytest tests/test_benchmarking_routes.py -v`
Expected: FAIL

Step 3: Add CRUD and refresh endpoints

Endpoints:
- `GET /api/v1/benchmarking/accounts`
- `POST /api/v1/benchmarking/accounts`
- `PATCH /api/v1/benchmarking/accounts/{id}`
- `POST /api/v1/benchmarking/accounts/{id}/refresh`
- `GET /api/v1/benchmarking/top-posts`
- `GET /api/v1/benchmarking/action-language-profile`

Step 4: Implement service skeleton

Channel policy:
- If official analytics/API access exists, use provider service stub.
- If unavailable, allow manual ingestion later; keep interface uniform now.
- Never fake success. Mark unsupported channels clearly in response.

Step 5: Run test to verify pass

Run: `cd backend && source .venv/bin/activate && pytest tests/test_benchmarking_routes.py -v`
Expected: PASS

Step 6: Commit

```bash
git add backend/services/benchmark_collector_service.py backend/routes/benchmarking.py backend/schemas/benchmarking.py backend/main.py backend/tests/test_benchmarking_routes.py
git commit -m "feat: add benchmark collector api skeleton"
```

---

## Task 7: Wire benchmark intelligence into strategy and copy generation

Objective: Ensure benchmark output affects actual generation, not just display.

Files:
- Modify: `backend/services/ai_service.py`
- Modify: `backend/services/growth_service.py`
- Modify: `backend/services/prompt_builder.py`
- Modify: `backend/routes/ai.py`
- Modify: `backend/schemas/ai.py`
- Test: `backend/tests/test_ai_generation_with_benchmark_context.py`

Step 1: Write failing integration test

```python
@pytest.mark.asyncio
async def test_generate_copy_accepts_engine_and_benchmark_overrides():
    payload = {
        "platform": "instagram",
        "topic": "봄 캠페인",
        "context": "",
        "engine": {"provider": "gpt", "model": "gpt-4.1"},
        "benchmark": {"top_k": 8, "client_id": "..."},
    }
    assert False
```

Step 2: Run test to verify failure

Run: `cd backend && source .venv/bin/activate && pytest tests/test_ai_generation_with_benchmark_context.py -v`
Expected: FAIL

Step 3: Extend request schemas

Add optional nested blocks:

```python
class EngineOverride(BaseModel):
    provider: str | None = None
    model: str | None = None

class BenchmarkOverride(BaseModel):
    client_id: UUID | None = None
    top_k: int | None = None
    window_days: int | None = None
```

Step 4: Inject benchmark profile into prompt builder

Prompt sections to append:
- top hooks
- top CTAs
- recommended sentence style
- forbidden copy similarities / originality note

Step 5: Route generation through new LLM router

Keep backward compatibility:
- no engine override → task policy/default provider
- no benchmark override → no benchmark enrichment or default policy value

Step 6: Run tests to verify pass

Run: `cd backend && source .venv/bin/activate && pytest tests/test_ai_generation_with_benchmark_context.py -v`
Expected: PASS

Step 7: Commit

```bash
git add backend/services/ai_service.py backend/services/growth_service.py backend/services/prompt_builder.py backend/routes/ai.py backend/schemas/ai.py backend/tests/test_ai_generation_with_benchmark_context.py
git commit -m "feat: apply benchmark intelligence to ai generation"
```

---

## Task 8: Add frontend AI engine settings page

Objective: Let admins switch Claude/GPT and adjust K-values from UI.

Files:
- Create: `frontend/src/app/(main)/settings/ai-engine/page.tsx`
- Create: `frontend/src/services/admin-ai-settings.ts`
- Modify: `frontend/src/app/(main)/settings/users/page.tsx`
- Modify: `frontend/src/app/(main)/settings/secrets/page.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx`
- Test: `frontend/src/app/(main)/settings/ai-engine/page.test.tsx`

Step 1: Write failing frontend test

```tsx
it("renders provider selector and top-k control", () => {
  render(<AIEngineSettingsPage />)
  expect(screen.getByText("AI 엔진 설정")).toBeInTheDocument()
  expect(screen.getByLabelText("기본 Provider")).toBeInTheDocument()
  expect(screen.getByLabelText("Top-K")).toBeInTheDocument()
})
```

Step 2: Run test to verify failure

Run: `cd frontend && npm test -- --runInBand page.test.tsx`
Expected: FAIL

Step 3: Add service wrapper

Methods:
- `listProviders()`
- `updateProvider()`
- `listTaskPolicies()`
- `updateTaskPolicy()`

Step 4: Build page UI

Required controls:
- default provider select
- model select per provider
- task policy table
- routing mode select
- top-k input
- benchmark window days input
- 4 scoring weight inputs
- fallback toggle
- save button per section

Step 5: Add navigation links

In settings tabs and sidebar, include `AI 엔진 설정`.

Step 6: Run test to verify pass

Run: `cd frontend && npm test -- --runInBand page.test.tsx`
Expected: PASS

Step 7: Commit

```bash
git add frontend/src/app/(main)/settings/ai-engine/page.tsx frontend/src/services/admin-ai-settings.ts frontend/src/app/(main)/settings/users/page.tsx frontend/src/app/(main)/settings/secrets/page.tsx frontend/src/components/layout/Sidebar.tsx frontend/src/app/(main)/settings/ai-engine/page.test.tsx
git commit -m "feat: add ai engine settings ui"
```

---

## Task 9: Add frontend benchmark center and composer controls

Objective: Surface top-K benchmark data and allow per-generation overrides.

Files:
- Create: `frontend/src/app/(main)/clients/[id]/benchmark/page.tsx`
- Create: `frontend/src/services/benchmarking.ts`
- Modify: `frontend/src/components/features/ContentComposer.tsx`
- Test: `frontend/src/components/features/ContentComposer.test.tsx`

Step 1: Write failing composer test

```tsx
it("shows engine selector and benchmark top-k override", () => {
  render(<ContentComposer mode="text" />)
  expect(screen.getByText("엔진 선택")).toBeInTheDocument()
  expect(screen.getByText("Top-K 벤치마킹")).toBeInTheDocument()
})
```

Step 2: Run test to verify failure

Run: `cd frontend && npm test -- --runInBand ContentComposer.test.tsx`
Expected: FAIL

Step 3: Add benchmarking service wrapper

Methods:
- `listAccounts(clientId)`
- `createAccount(payload)`
- `refreshAccount(id)`
- `getTopPosts(clientId, platform, topK)`
- `getActionProfile(clientId, platform)`

Step 4: Extend content composer

Add:
- provider/model select or simplified engine dropdown
- benchmark top-k override input
- toggle `상위 포스트 패턴 반영`
- preview card for top hooks / CTAs

Step 5: Create client benchmark page

Show:
- registered benchmark accounts
- platform tabs
- top post list sorted by benchmark score
- action-language summary cards

Step 6: Run tests to verify pass

Run: `cd frontend && npm test -- --runInBand ContentComposer.test.tsx`
Expected: PASS

Step 7: Commit

```bash
git add frontend/src/app/(main)/clients/[id]/benchmark/page.tsx frontend/src/services/benchmarking.ts frontend/src/components/features/ContentComposer.tsx frontend/src/components/features/ContentComposer.test.tsx
git commit -m "feat: add benchmark center and composer engine controls"
```

---

## Task 10: Verification and rollout checklist

Objective: Verify the end-to-end feature works without breaking existing SNS flows.

Files:
- Create: `docs/plans/verification-2026-04-20-multi-llm-engine-checklist.md`
- Modify: `docs/TASK-SNS-멀티LLM엔진-8채널벤치마킹-260420.md` (implementation status section)

Step 1: Backend verification

Run:
```bash
cd backend && source .venv/bin/activate && pytest tests/test_llm_router.py tests/test_admin_ai_settings.py tests/test_benchmarking_routes.py tests/test_ai_generation_with_benchmark_context.py -v
```
Expected: all PASS

Step 2: Frontend verification

Run:
```bash
cd frontend && npm test -- --runInBand
npm run build
```
Expected: tests pass, build succeeds.

Step 3: Manual QA

Check:
- `/settings/ai-engine` loads
- provider/model changes persist
- `Top-K` changes persist
- benchmark page shows top posts
- content composer sends engine override
- generation still works when benchmark disabled
- existing `/settings/secrets` still works

Step 4: Update docs

Add status notes to task doc:
- implemented
- deferred
- unsupported channels clearly labeled

Step 5: Commit

```bash
git add docs/plans/verification-2026-04-20-multi-llm-engine-checklist.md docs/TASK-SNS-멀티LLM엔진-8채널벤치마킹-260420.md
git commit -m "docs: add verification checklist for multi llm benchmark rollout"
```

---

## Notes for implementation

- Do not claim 8-channel live benchmark ingestion unless each channel’s data path is actually wired.
- For unsupported platforms, return explicit `unsupported` or `manual_ingest_required` status.
- Keep existing Claude CLI path intact until router migration is verified.
- Do not hardcode any GPT keys or provider URLs.
- Preserve current content creation UX while adding new controls gradually.
- Prefer deterministic benchmark extraction first; add LLM-assisted summarization after raw pipeline is stable.

## Recommended execution order

1. Tasks 1-4 first (data + router + settings API)
2. Tasks 5-6 next (benchmark intelligence core)
3. Tasks 7-9 after backend is stable
4. Task 10 only after manual QA

## Execution status snapshot (2026-04-20)
- Tasks 1-9: implemented
- Task 10 verification: in progress, core checks passed
- Passed:
  - backend py_compile
  - frontend production build
  - alembic stamp 005 + upgrade 006
  - new tables existence check
  - default provider/task-policy seeding check
- Remaining:
  - real 8-channel live collectors
  - richer automated tests
  - final cleanup/commit
