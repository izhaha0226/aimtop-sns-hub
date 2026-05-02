# Topic-Based Multi-Channel Distribution Implementation Plan

> **For Hermes:** Implement only after representative approval. This is a product/architecture shift, not a small UI patch.

**Goal:** Change SNS Hub from “create separate Instagram/card/text/Threads items first” to “create one campaign topic, generate one shared visual concept/assets, then produce channel-optimized variants for Instagram, Facebook, Threads, X, etc. and distribute each variant to its best channel.”

**Architecture:** Introduce a parent `content_topics` concept and keep existing `contents` as child channel variants. A topic owns the common strategic brief and canonical image/visual system. Each child content stores the per-channel copy, hashtags, image crop/format, publish target, and status.

**Current finding:** The current composer hard-routes by mode: card news → Instagram, text → Threads. `contents` has no parent topic field. `source_metadata` can temporarily hold variant metadata, but a durable parent-child field is needed for filtering, approval, and grouped publishing.

---

## Required Product Behavior

1. User enters one topic/brief once.
2. System generates the **5-card card-news storyline first** before image generation.
3. System generates **three first-slide visual directions only** for selection:
   - Photorealistic option 1
   - Photorealistic option 2
   - Illustration option 3
4. User chooses one visual direction from the first-slide previews.
5. System generates the remaining 4 card images using the selected visual direction and the pre-approved 5-card storyline.
6. System creates **channel variants** from that topic:
   - Instagram: visual-first, 5-card carousel, concise caption, hashtags, square/card/feed style
   - Facebook: same campaign visual adapted for feed, context-rich copy, community/relationship tone, link/CTA-friendly
   - Threads: text-first conversation opener, short cadence, reply bait, image optional or first-card summary image
   - X: compressed hook/thread-ready format if enabled
   - Blog/long-form if enabled: expanded narrative using the same campaign spine
7. Each variant can be reviewed/editable independently.
8. Approval can be topic-level or variant-level, but external publishing remains per channel with existing token/evidence checks.
9. Publishing evidence must remain per child content: `platform_post_id`, `published_url`, `publish_error`, `channel_connection_id`.

---

## Data Model

### Task 1: Add parent topic model

**Create:** `backend/models/content_topic.py`

Fields:
- `id UUID primary key`
- `client_id UUID FK clients.id`
- `author_id UUID FK users.id nullable`
- `title VARCHAR(500)`
- `brief TEXT nullable`
- `objective VARCHAR(100) nullable` — awareness / engagement / conversion / retention
- `target_audience TEXT nullable`
- `core_message TEXT nullable`
- `card_storyline JSON nullable` — five cards before image generation. Each card stores `card_no`, `headline`, `body`, `visual_brief`, `cta_or_transition`.
- `reference_assets JSON nullable` — uploaded images/files used as reference or compositing inputs. Each asset stores `url`, `asset_type`, `usage_mode`, `memo`, `target_cards`.
  - `asset_type`: product / person / place / logo / brand_style / competitor_reference / moodboard / raw_material
  - `usage_mode`: reference_only / must_include / composite_subject / style_reference / do_not_copy_structure
- `visual_options JSON nullable` — first-slide preview candidates: photorealistic_1, photorealistic_2, illustration_3 with prompt/image/rationale.
- `selected_visual_option VARCHAR(50) nullable`
- `shared_visual_prompt TEXT nullable`
- `shared_media_urls JSON nullable` — final 5-card image URLs after visual option selection.
- `benchmark_context JSON nullable`
- `status VARCHAR(50)` — draft / variants_generated / pending_approval / approved / scheduled / partially_published / published / failed
- `source_metadata JSON nullable`
- `created_at`, `updated_at`

### Task 2: Link contents to topic

**Modify:** `backend/models/content.py`

Add:
- `topic_id UUID nullable FK content_topics.id index`
- `target_platform VARCHAR(50) nullable index`
- `variant_role VARCHAR(50) nullable` — feed / card_news / text_post / thread / story / reel / blog

**Modify:** `backend/main.py ensure_columns()`

Add `ALTER TABLE` syncs:
- `content_topics` table creation if using create_all with imported model
- `contents.topic_id`
- `contents.target_platform`
- `contents.variant_role`

### Task 3: Schemas

**Create:** `backend/schemas/content_topic.py`

Include:
- `ContentTopicCreate`
- `ContentTopicUpdate`
- `ContentTopicResponse`
- `ChannelVariantRequest` with `platforms: list[str]`
- `TopicVariantResponse` with `topic` and `variants`

**Modify:** `backend/schemas/content.py`

Add optional response/create fields:
- `topic_id`
- `target_platform`
- `variant_role`

---

## Generation Service

### Task 4: Create channel strategy rules

**Create:** `backend/services/channel_variant_strategy.py`

Rules:
- Instagram: 1:1 or 4:5 image, visual hook, short caption, 8-15 hashtags, CTA in final line
- Facebook: 1.91:1 or square accepted, stronger context, less hashtag-heavy, community tone
- Threads: no heavy poster text required, conversational first line, 1-2 hashtags max or none
- X: 280-char variant + optional thread outline
- LinkedIn: professional insight framing, proof/lesson structure
- Kakao: benefit/notice style, Korean clarity, CTA direct

### Task 5: Create topic generation service

**Create:** `backend/services/topic_distribution_service.py`

Responsibilities:
1. Build Supermarketing topic brief.
2. Generate the **5-card storyline first**:
   - Card 1: hook / promise / strongest visual entry
   - Card 2: problem or context
   - Card 3: mechanism / proof / differentiation
   - Card 4: benefit / scenario / objection handling
   - Card 5: CTA / next action / brand closure
3. Accept uploaded reference/composite assets before visual generation:
   - product/person/place/logo images that must appear in the output
   - brand style or moodboard references
   - competitor/reference screenshots used for structure only, never copied
   - per-card targeting, e.g. asset A appears on cards 1 and 5 only
4. Generate three first-slide preview candidates only:
   - `photorealistic_1`
   - `photorealistic_2`
   - `illustration_3`
5. Wait for user selection of the visual option.
6. Generate all five card images using:
   - selected visual style
   - fixed 5-card storyline
   - uploaded reference/composite assets according to their `usage_mode` and `target_cards`
   - consistent typography/layout/brand treatment
   - card-specific visual briefs
7. For each selected channel, generate optimized copy + metadata using the same campaign spine and final media URLs.
8. Create one `Content` child per channel using the shared media URLs but channel-specific text/hashtags/post_type/target_platform/source_metadata.

Important rules:
- Benchmark structure only. Do not copy competitor wording/slogan/layout.
- Store generation rationale in `source_metadata.channel_strategy`.
- Store `source_metadata.shared_topic_id` and `source_metadata.shared_visual_prompt` for traceability.

---

## API

### Task 6: Add topic routes

**Create:** `backend/routes/content_topics.py`

Endpoints:
- `GET /api/v1/content-topics`
- `POST /api/v1/content-topics`
- `GET /api/v1/content-topics/{topic_id}`
- `PUT /api/v1/content-topics/{topic_id}`
- `POST /api/v1/content-topics/{topic_id}/generate-storyline` — creates the 5-card text/storyline before image generation
- `POST /api/v1/content-topics/{topic_id}/reference-assets` — attach uploaded/reference/composite image assets with usage mode and target cards
- `POST /api/v1/content-topics/{topic_id}/generate-visual-options` — generates first-slide previews only: photorealistic 1, photorealistic 2, illustration 3
- `POST /api/v1/content-topics/{topic_id}/select-visual-option` — stores selected image type
- `POST /api/v1/content-topics/{topic_id}/generate-card-images` — generates all five card images from the selected style, storyline, and reference assets
- `POST /api/v1/content-topics/{topic_id}/generate-variants`
- `POST /api/v1/content-topics/{topic_id}/request-approval`
- `POST /api/v1/content-topics/{topic_id}/approve`

**Modify:** `backend/main.py`

Register `content_topics` router.

---

## Frontend

### Task 7: Replace entry UX

**Modify:** `frontend/src/app/(main)/contents/new/page.tsx`

Current: choose text or card-news first.

New: “주제 기반 멀티채널 캠페인 만들기” first.

Fields:
- Client
- Topic title
- Objective
- Core message / offer
- Audience
- Channels checkboxes: Instagram, Facebook, Threads, X, LinkedIn, Kakao, Blog, YouTube/TikTok optional
- Benchmark channels
- Reference/composite image upload area:
  - product/person/place/logo images to include
  - brand style/moodboard images to reference
  - competitor/reference screenshots for structure only
  - per-asset usage mode: reference only / must include / composite subject / style reference / do not copy structure
  - target card selector: all cards or specific cards 1-5

Keep legacy buttons under “단일 콘텐츠 빠른 작성” for backwards compatibility.

### Task 8: Add topic composer page

**Create:** `frontend/src/app/(main)/contents/new/topic/page.tsx`

Flow:
1. Write topic brief.
2. Select channels.
3. Upload optional reference/composite images and label usage:
   - 합성 필수: output에 실제로 포함
   - 참고만: 분위기/스타일 참고
   - 브랜드 자산: 로고/제품/공간/인물
   - 벤치마킹: 구조만 참고, 복제 금지
4. Click “5장 카드뉴스 내용 먼저 생성”.
5. Show editable 5-card storyline before any image generation.
6. User edits/approves each card's headline/body/visual brief and maps uploaded assets to cards if needed.
7. Click “첫 장 시안 3개 생성”.
8. Show only Card 1 previews:
   - 실사형 1안
   - 실사형 2안
   - 일러스트형 3안
9. User chooses one visual type.
10. Click “선택한 스타일로 5장 전체 이미지 생성”.
11. Show final 5-card carousel images.
12. Generate Instagram/Facebook/Threads/etc. channel-specific copy from the same storyline and image set.
13. Save all as grouped drafts.

### Task 9: Add topic detail page

**Create:** `frontend/src/app/(main)/content-topics/[id]/page.tsx`

Show:
- topic summary
- shared image
- variants grouped by channel
- status per variant
- approve/schedule/publish controls per variant

### Task 10: Update contents list

**Modify:** `frontend/src/app/(main)/contents/page.tsx`

Add group indicator:
- if `topic_id` exists, show “같은 주제 N개 변형”
- filters: topic / platform / status

---

## Verification

1. Backend unit smoke:
   - Create topic
   - Generate 5-card storyline first and verify no image call happens before storyline exists
   - Upload/reference at least one asset with `usage_mode=must_include` and `target_cards=[1,5]`
   - Generate first-slide visual options and confirm exactly 3 candidates exist: `photorealistic_1`, `photorealistic_2`, `illustration_3`
   - Confirm visual option prompts include relevant reference asset instructions without copying competitor assets
   - Select one visual option
   - Generate 5 final card images and confirm all 5 follow the selected visual type and card-targeted asset instructions
   - Generate variants for `instagram,facebook,threads`
   - Confirm 1 topic + 3 contents are created
   - Confirm variants share the final 5-card media URL set where channel-appropriate
   - Confirm copy differs per channel
2. Frontend build:
   - `cd frontend && npm run build`
3. Runtime:
   - restart `com.aimtop.sns-frontend`
   - `curl -I http://127.0.0.1:1111/login`
   - `curl -I https://sns.aimtop.ai/login`
4. Evidence:
   - DB query shows parent topic and child contents linked by `topic_id`
   - generated variants have `target_platform` values
   - publish evidence remains per content child, not topic-level

---

## Implementation Order

1. Backend model/schema/API minimal topic CRUD.
2. Add `topic_id`/`target_platform` to existing contents safely.
3. Add reference/composite asset upload mapping to topic composer.
4. Implement 5-card storyline generator before any image generation.
5. Implement first-slide 3-option visual preview generator using reference assets.
6. Implement selected-style 5-card image generation with per-card asset mapping.
7. Service that generates channel variants using current AI/image services.
8. Frontend topic composer MVP.
9. Topic detail/grouped list UX.
10. Build/restart/prod verify.

---

## Non-Goals for MVP

- Do not rewrite the publisher.
- Do not remove existing text/card-news creation routes.
- Do not claim external publish success without platform evidence.
- Do not create final images before the 5-card storyline is visible and editable.
- Do not ignore uploaded reference/composite assets; every uploaded asset must have a visible usage mode and target-card mapping.
- Do not use competitor/reference images as copy targets; they are structure/mood references only unless the user marks own brand/product asset as `must_include`.
- Do not create all 5 images for all three visual styles; only Card 1 is generated for the 3-option preview stage.
- Do not create separate images per channel first; selected campaign card set comes first, channel crops/variants come second.
