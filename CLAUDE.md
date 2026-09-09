# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

**Conda Environment**: `rag-local` (Python 3.11+)

All operations must use this conda environment:
```bash
conda activate rag-local
```

## Project Information

**Name**: QueryMind（智询）  
**Version**: 0.6.2.1  
**Language Support**: Bilingual (Chinese/English) via i18next  
**License**: MIT

## Common Commands

### Backend

**Start Development Server**
```bash
uvicorn app.api.main:app --reload --port 8000
# Alternative entry point:
uvicorn app.main:app --reload --port 8000
```

**Linting and Formatting**
```bash
ruff check .                        # Lint check
ruff format .                       # Format code
```

Note (2026-08-28, counts refreshed 2026-09-05): `tests/` and `scripts/` were cleared ahead
of the v0.7 rewrite. `scripts/` was down to one file then and holds nine now — `audit/frontend_audit.py`,
`audit/cognitive_complexity.py`, `audit/reachability.py`, `check_lock_wheels.py`, `check_sensitive.py`, `ci_import_environment.py`,
`create_admin.py`, `eval_retrieval.py`, `verify_config_centre.py` — each added with the thing it verifies,
and still no `scripts/init_db.py`. `tests/` is being rebuilt incrementally alongside bug fixes — see
Testing Strategy below.

**Tests and lint**
```bash
make test                           # pytest -q
make test-ci                        # the same suite, with CI's optional packages hidden
make lint                           # ruff check . && ruff format --check .
```

**`make test-ci` before pushing.** A development machine accumulates optional
packages that `requirements/ci.txt` does not install -- pytesseract, pdfplumber,
sentence-transformers -- and a test that touches one inherits it silently, so it
is green here and red there, and only after a push.
`scripts/ci_import_environment.py` makes that set unimportable for one run. It
blocks at the `sys.meta_path` finder rather than by replacing `__import__`,
because a genuinely absent package is still satisfied from `sys.modules` and a
test that injects a fake there must keep working -- the first version got that
wrong and reported a failure CI does not have, which is worse than no simulation:
it sends you to fix code that is not broken.
`tests/core/test_ci_import_environment.py` checks the blocked set against
`requirements/ci.txt` in both directions, so it cannot claim CI lacks something
CI installs, and cannot shrink to nothing and keep reporting success.

**Optional services and offline evaluation**
```bash
make up                             # start Neo4j for local dev (Browser on :7474)
make down                           # stop it
make eval-retrieval                 # BM25 retrieval quality over config/eval/ (no model needed)
```

Note (2026-08-29): A backend agent audit found several components documented above
that no longer matched the running code — an orphaned router/clarification rewrite
(`app/agents/router/{enhanced_service,hybrid_clarification,accuracy,frontend_integration,validator,adapter,pipeline}.py`),
an orphaned RAG fusion/vector duplicate (`app/agents/rag/{fusion.py::fuse_evidence,enhanced_vector.py}`),
an orphaned second quality-scoring engine (`app/agents/validation/quality_orchestrator.py`),
and an unreachable ReAct tool loop (`app/agents/tool/react.py`). All were deleted; the
claims above were corrected to describe what actually runs today.

Note (2026-08-29, second pass): A full-backend audit found the chat path was not
persisting messages, conversation context was filled but never read, the query
endpoint never returned its execution_id, the `graph` route never queried the
graph, and 184 modules (~13,000 lines) had zero importers. All were fixed or
deleted; `app/` went from 583 to 371 Python files and Settings from 261 to 216
fields. Those are what the audit left behind, not a ceiling — today it is 372 files and
235 settings fields (2026-09-05). See `docs/superpowers/plans/2026-08-29-backend-full-audit-remediation.md`
for the plan, what was deliberately left dormant, and what remains open.

### Frontend

**Start Development Server**
```bash
cd frontend
npm install                         # First time only
npm run dev                         # Starts Vite dev server (port 5173)
```

**Build for Production**
```bash
cd frontend
npm run build                       # TypeScript compile + Vite build
npm run preview                     # Preview production build (port 4173)
```

**Checks and visual verification**
```bash
cd frontend
npm run lint                        # eslint, gates on errors (warning ratchet: 25)
npm run type-check                  # tsc -b --noEmit
npm run lint:design                 # shape/depth scale ratchet (see Frontend styling)
npm test -- --run                   # vitest (.test.ts and .test.tsx)
npm run screenshots                 # both servers up; PNGs of 8 app states
```

CI runs everything above except `screenshots`, which is a local before/after tool
by design — see [Frontend styling](#frontend-styling-adopted-2026-08-31) for when to
reach for which.

### Docker Deployment

```bash
export OPENAI_API_KEY="your-api-key"
./deploy/scripts/deploy.sh production balanced
```

Configuration lives in `config/` and runtime files in `.runtime/`.

## Architecture Overview

### Pragmatic RAG System in Transition

This is a **working RAG system** built on proven components (LangChain, ChromaDB, FastAPI). The system evolved from a multi-agent LangGraph architecture and is currently in a **transition state** - core functionality is stable, but the architecture is being incrementally modernized.

**Current architecture**: Legacy retrieval and synthesis components wrapped with adapter services for cleaner interfaces. The `RAGPipeline` provides the public API, while `OrchestrationEngine` coordinates execution flow.

**What works well**: Retrieval quality, answer synthesis, bilingual support, session management.

**What's being improved**: Service boundaries, configuration management, error handling consistency.

### Core Components

The system has **3 primary components** and **3 optional components**:

**Primary (always active)**:
1. **Router** ([app/agents/router/service.py](app/agents/router/service.py))
   - Query intent classification and route selection

2. **Retriever** ([app/agents/rag/service.py](app/agents/rag/service.py))
   - Hybrid search: vector (ChromaDB) + BM25 + reranking
   - Optional: Knowledge graph (Neo4j), web search

3. **Synthesizer** ([app/agents/synthesizer/service.py](app/agents/synthesizer/service.py))
   - Citation-first answer generation from evidence

**Optional (route-dependent)**:
4. **Planner** - Task decomposition for complex queries
5. **Tool Runner** - Governed connector actions, selected by a model from a
   schema-declared catalogue (`app/agents/tool/selector.py` + `service.py`,
   reworked 2026-08-30). Two actions are registered (2026-09-04): a `read` that
   lists the caller's own connectors (`querymind_connector_list_owned`) and a
   `write` that disables one (`querymind_connector_disable_owned`). The read is
   what makes the loop worth having -- it is how the model finds the id of a
   connector before acting on it, and `operation="read"` skips approval entirely
   so it costs the user no confirmation. Its summary is composed from
   `connector_id` and `status` alone, never `ConnectorView.name`: a read-only
   tool's summary *is* fed back as a `ToolObservation`, `name` is user-authored
   free text, and a summary built from a `^[a-z][a-z0-9_-]{0,63}$` id and a
   two-value Literal is structurally incapable of carrying an instruction. That
   is what makes the read-then-write composition safe rather than untested, and
   `tests/security/test_connector_list_tool_scoping.py` pins it. Selection is **multi-step**: select → invoke → observe → repeat,
   bounded by `TOOL_MAX_STEPS` (default 3) and by the shared
   `STAGE_TIMEOUT_TOOL_MS` ceiling. The loop stops on anything other than a clean
   success — an `approval_required` result means the action has *not* happened,
   so planning a next step on top of it would be reasoning from a false premise —
   and it stops if the model repeats a call it already made.

   **The selector is deliberately blind to retrieved content.** Its inputs are
   the user's question, the conversation, and the tool catalogue; it takes no
   `EvidenceBundle`/`ContextBundle`, and `ToolRunner` no longer receives evidence
   either, so there is no argument to pass by mistake. Retrieved chunks are
   attacker-controllable the moment one user can put a document where another
   user's query will retrieve it, and a model that chose tools from them would
   put this system in the middle of the lethal trifecta. While selection was a
   regex over the question this was true by accident;
   `tests/security/test_tool_selection_is_evidence_blind.py` makes it a property.
   If a tool ever genuinely needs retrieved content, that is a deliberate change
   with its own threat model.

   **Feeding results back re-opens that question one layer down**, which is what
   `ToolRisk == "open_world"` now answers: such a tool reaches content this
   system does not control, so its summary is somebody else's writing and
   contributes only its id and status to the next decision, never its text
   (`app/agents/tool/service.py::_observation`). Every tool registered today
   composes its own summary, so today they all contribute it.

   Arguments come from a model now, so `ToolDefinition.parameters` (name,
   required, `max_length`, `pattern`) is the only thing between it and the
   executor; `ToolRegistry.invoke` validates against it before spending an
   approval round trip, and `ToolRegistry.catalog(actor)` only offers tools the
   actor is authorized to run.

   A `write` tool always returns `approval_required` on its first call; the
   caller confirms and re-sends with the token. See "Governed tool stack" below.
6. **Finalizer** - Quality validation and safety checks

### Pipeline Profile

The system runs a single profile, **advanced** (web research and full quality
validation). `ExecutionPolicy.for_profile` in `app/orchestration/policies.py` is the
only place that decides what a profile enables. A parallel set of descriptors in
`app/pipeline/profiles.py` (`ProfileCapabilities`, `CapabilityBudget`,
`PROFILE_DEFINITIONS`) had no readers and had drifted into contradicting the policy;
it was deleted on 2026-08-29, leaving only the `PipelineProfile` enum.

### Execution Flow

```
Request → RAGPipeline.execute()
   ↓
OrchestrationEngine
   ↓
1. Router → determines query type and route
2. Planner → (optional) decomposes complex queries
3. Retriever → gathers evidence from vector/BM25/graph/web
4. Tool Runner → (optional) multi-step governed tool loop, react route only
5. Synthesizer → generates answer with inline citations
6. Finalizer → (optional) validates quality and safety
   ↓
PipelineResult → returned to caller
```

**Note**: Steps 2, 4, 6 are conditionally executed based on route and profile settings. The flow is sequential with concurrent retrieval from multiple sources in step 3.

### Quality Assurance

**Validation layers** (applied based on profile):
1. **Route confidence checks**: Threshold-based validation
2. **Retrieval quality scoring**: none. A local-LLM (Ollama) batch relevance scorer existed in `app/agents/rag/relevance.py` with no callers anywhere in the request pipeline; it was deleted on 2026-08-29. Retrieval results are not quality-scored.
3. **Answer validation**: Citation completeness, hallucination detection, NLI checks
   (**switched on 2026-09-04; before that this line was false**, see below), and
   **sentence grounding** — `apply_sentence_grounding`
   (`app/services/retrieval/citation_grounding.py`), reached from
   `app/orchestration/finalization.py`, scores each sentence's token overlap with the
   evidence and hedges the ones under 0.22. It skips sentences that make no claim, which is
   not a nicety: it once counted a bare `[1]` as a sentence, found it unsupported, and
   hedged the attribution instead of the claim.

   **It spliced hedges into the middle of words until 2026-09-05.** The hedge is inserted
   by *offset* into the raw answer, and the offsets are computed against a protected copy
   in which dots that are not sentence boundaries are substituted out. Two things made
   those offsets wrong. The sentinel was `"<ABBR>"` — six characters replacing one — beside
   a comment asserting the substitution "never shifts a position"; it is `chr(0xE000)` now,
   one character, and the comment is true. And abbreviations were matched as bare
   substrings, so `"p."` matched inside "setup.", `"ed."` inside "used." / "based." /
   "updated." / "required.", and `"no."` inside "casino." — ordinary English sentence
   endings, which therefore did not split, and shifted every offset after them. Measured:

   ```
   in:  Access is based. The retention window is ninety days. Backups run nightly.
   out: Access is based. The retention window is ninety days. Backu基于当前可用证据，Backups run nightly.
   ```

   The same loop tried only `abbr` and `abbr.upper()`, so "Dr." — how anyone actually
   writes it — was the one form it did *not* protect. `_ABBREVIATION_RE` is anchored on a
   non-alphanumeric boundary, longest-first so `"pp."` beats `"p."`, and case-insensitive.

   This is the failure this file already described for URLs, reaching ordinary prose,
   because the same substitution caused both. It was found by chasing a SonarCloud
   `python:S1192` (`"<ABBR>"` duplicated four times) — the duplicated literal was not the
   defect, but reading the four sites together is what exposed one that was.
   `tests/services/test_sentence_grounding_offsets.py` pins it, and every assertion in it
   was verified to fail against the previous commit.

   **The NLI stage had never run, and three separate defects meant turning it on would
   have been worse than leaving it off** (all fixed 2026-09-04). The switch was
   `CASCADE_ENABLE_LEVEL2`, defaulting false — and the numbering was itself wrong:
   `enable_level2` gated NLI while `enable_level3` gated the citation check, so reading
   the configuration told you the opposite of what ran. The switches are named for their
   stages now (`CASCADE_ENABLE_RULES` / `_CITATIONS` / `_NLI` / `_DEEP`), and two of the
   four timeout settings were deleted because nothing consumed them — note that
   `test_settings_have_readers` passed for both, since **assigning a field to an attribute
   nobody reads counts as a reader**.

   The three defects, in increasing order of how badly they would have hurt:

   - **It blocked the event loop.** `model.predict` — a synchronous cross-encoder forward
     pass — ran directly inside `async def`, with no `to_thread`, no timeout and no
     breaker; the loader ran there too, without `local_files_only=True`, so a machine
     without the model would have started an untimed download inside a request. It now
     copies `rerank_evidence` exactly: sync core, `wait_for(to_thread(...))`, circuit
     breaker, deterministic fallback.
   - **The deterministic fallback could not score Chinese.** It tokenised with `\w+`, and
     `\w` matches CJK, so a whole clause became one token. Measured: a verbatim clause
     copy scored 1.00, but a paraphrase, a recombination of two sources, and an added
     connective all scored **0.00** — and synthesis paraphrases by construction. A 0.00
     becomes `factuality < 0.7`, then a retry, then a rejected answer.
   - **The scoring was inverted.** The code read `scores[:, 2]` as the entailment column,
     but the configured model's `id2label` is `{0: contradiction, 1: entailment,
     2: neutral}` — column 2 is *neutral* — and those are raw logits that were clamped
     into [0,1] rather than softmaxed. Measured against the real model: an entailed
     sentence scored **0.000** and an unrelated one **0.894**. The column now comes from
     the model's own `id2label` (so a different `NLI_MODEL_NAME` still works) and the row
     is softmaxed: 0.993 / 0.001 / 0.000 for entailed / contradicting / unrelated.

   **The model is English and the system is bilingual**, so the cross-encoder runs only on
   predominantly-Latin text; everything else takes the repaired deterministic path.
   `CascadeResult.backend` records which ran and `validation_method` reports
   `standard_lexical` rather than `standard` when it was not the cross-encoder — a method
   name that claims a check happened when it did not is the failure this file keeps
   describing. Shipping a Chinese-capable NLI model is a separate evaluation project.

   `CASCADE_*` is not in `config_schema.py`, but the reason changed on 2026-09-04. It
   used to be that `_get_validation_cascade` caches a module-global `ValidationCascade`
   that `apply_config_reload` did not clear, so an admin edit would have reported success
   and changed nothing until restart. `clear_validation_caches()` now runs in the reload
   sequence -- dropping the cascade *and* the `lru_cache`d NLI model, which is keyed on
   `NLI_MODEL_NAME` -- so that blocker is gone and whether to expose these is now an
   ordinary decision about what an operator should be able to change mid-flight, not a
   workaround for a stale cache.
4. **Safety checks**: one pattern set, `app/services/security/outbound_redaction.py`,
   enforced at three points. Matches become stable `<KIND_n>` tokens, so the same value
   twice in one text gets the same token and the model can still reason about "that
   number" — and the counts returned to the caller never carry the matched value.

   | boundary | where | default |
   |---|---|---|
   | the question | `privacy_permission` node, `inspect_input` | mandatory, no `on_timeout` |
   | LLM + embedding egress | the model wrapper, `redact_messages_for_provider`, external providers only | `OUTBOUND_LLM_REDACTION_ENABLED` / `..._EMBEDDING_...`, both true |
   | the answer | `output_filter` node, `filter_output` | a `MANDATORY_STAGES` member |
   | image egress | `app/privacy/image_egress.py`, `ImageMaskingService`, external providers only | fail-closed, no switch |

   **An image is a payload the text redactor cannot read** (wired 2026-09-05).
   `describe_image_with_vision` base64s the image into an `image_url` data URI and posts
   it to the configured vision backend. It calls `redact_messages_for_provider` on that
   payload, which is exactly why the gap was invisible: an outbound control *does* run
   there, it is simply the wrong kind. It redacts text and leaves the data URI
   byte-identical -- correctly, since mangling it would corrupt the image -- so a user's
   image reached OpenAI as uploaded. Verified against the previous commit: byte-identical.

   `ImageMaskingService` (`app/privacy/image_masking.py`) already existed and already
   worked: local OCR locates text matching `INPUT_KINDS`, the regions are painted out, and
   asked for an `external` derivative it cannot produce it returns `safe_for_external=False`
   with no content. **Nothing called it.** Its two entry points were
   `ImageProcessor._masked_bytes`, whose own docstring reads "Fail closed so OCR and every
   external VLM consume only a safe derivative", on a class ingestion constructs but calls
   exactly one *other* method on -- and `PrivacyService.mask_images`, which has no callers
   either. A control that is written, tested and unreachable is the failure this file keeps
   recording, in its most expensive form.

   `_bytes_for_backend` now masks before an external backend and returns the original to a
   local one, splitting them with `is_external_provider` rather than a second list --
   ollama is not in it, and a local endpoint sits inside the same boundary as the OCR that
   would do the masking. Three consequences worth knowing:

   - **The detector is Tesseract, so fail-closed couples captioning to OCR.** A machine
     that cannot inspect an image may not send one. On the `auto` order that degrades to
     the local model; with `IMAGE_CAPTION_BACKEND=openai` it means no caption, which is the
     right answer to "I cannot see what is in this image". `GET /admin/model-settings/effective`
     reports it -- and `_ocr`'s "images are still searchable if captioning is on" was
     corrected in the same pass, because it is now true only of a local backend.
   - **A refusal is not an outage.** `describe_image_with_vision` returns
     `image_masking_blocked` when every attempted backend was blocked, rather than folding
     it into `vision_failed`.
   - **Masking is not a blanket re-encode.** With no sensitive region found the original
     bytes go out unchanged, which is what keeps the assertion above meaningful rather than
     passing because everything is altered.

   `IMAGE_CAPTION_ENABLED` defaults false, so this was latent rather than shipping -- and
   it stopped being latent when that switch became editable from the admin page.
   `tests/security/test_image_masking_reaches_the_vision_call.py` pins all of it, including
   the redactor's byte-identical pass-through, so nobody reasons from its presence to the
   image being covered.

   `app/services/answer_safety.py` (OpenAI-style keys, AWS key ids, private-key headers,
   `password=`/`token=`) is not a rival set: `filter_output` composes it with the shared
   one. `app/agents/validation/rules.py` does keep its own SSN/credit-card/email/phone
   patterns, and runs inside the validation cascade reached through the verifier.

   **China-specific identifiers were added on 2026-09-04, and there were none before
   that.** Resident ID cards, bank cards and mainland mobile numbers were caught anyway —
   all three are long digit runs, so the generic `PHONE` rule swallowed them — but every
   one was *reported* as a phone number, which makes a privacy finding describe something
   that did not happen, and a passport number (eight digits, one under that rule's
   minimum) was reported as nothing at all. `ID_CARD_CN`, `MOBILE_CN`, `BANK_CARD`,
   `PASSPORT_CN` and `USCC_CN` now match ahead of `PHONE`, which is load-bearing: patterns
   apply in order and the first to match owns the span, so a specific rule placed after
   the generic one is indistinguishable from not having written it. IPv6 landed in the
   same pass; only IPv4 had been covered.

   Order matters *among* the specific rules too, and the first attempt got it wrong in
   both directions. `USCC_CN` ahead of `BANK_CARD` claimed every 18-digit order number as
   a company registration, because the credit-code alphabet includes digits; putting the
   digits-only rule first fixes it, since a real credit code carries letters. Then
   `BANK_CARD`'s right boundary of `(?!\d)` turned out to be satisfied by a *letter*, so
   it took the seventeen leading digits out of a credit code ending in its checksum letter
   — the boundary has to be non-alphanumeric. And `[EGDSPH]` plus eight digits is also how
   a dated document id is written (`E20260904`), so the passport rule excludes eight
   digits that read as a calendar date: a passport number that happens to spell a recent
   date is rare, and redacting every document reference of that shape corrupts text the
   model has to reason about.

   All three came out of an adversarial false-positive pass, and none of them would have.
   The first such pass reused inputs already known to be clean, so it reported zero
   findings and could not have reported anything else — the same defect as a secret
   scanner nobody has watched fail. `tests/security/test_chinese_pii_redaction.py` pins
   each one.

   **A kind must be added in two places.** `redact_sensitive_text` skips anything outside
   `allowed_kinds`, and those sets are `PII_KINDS`/`INPUT_KINDS`/`OUTPUT_KINDS` in
   `app/privacy/text.py`. A pattern added only to `outbound_redaction.py` compiles, reads
   correctly and matches nothing; `test_every_pattern_kind_is_reachable` is the guard.
   `URL` is the one kind deliberately in `INPUT_KINDS` and not `OUTPUT_KINDS` — an answer
   keeps its links.

   `app/agents/rag/web.py::_sanitize_query` used to be a fourth set, seven hand-written
   patterns, and the weakest: it missed a mainland mobile number (eleven digits, under its
   13-digit card threshold), an API key, a Bearer token, an internal URL and a Windows
   path. It never leaked, because `privacy_permission` redacts the question before the web
   retriever sees it — which is exactly why it was worth deleting rather than extending. A
   boundary that only appears to be guarded is worse than an unguarded one: weakening the
   layer that does the work would have shown up there as nothing at all. It now calls the
   shared redactor, and the second pass is kept because a search engine is outside every
   agreement this system has.

   **This system does not look for faces in a user's image** (deleted 2026-09-05).
   `app/ingestion/extraction/people.py` ran OpenCV face/HOG detection over every ingested
   image, and `build_people_summary` rendered `human_present`, `person_count` and
   `face_count` into the same `page_content` as the OCR text -- for a standalone uploaded
   image, that string *is* the chunk, indexed into the main corpus through both vector and
   BM25. It was on by default, so nobody chose it; **nothing in `app/` or the frontend read
   any of the five fields it produced**, so the exposure bought nothing; and this section,
   which exists to say what is and is not covered, did not mention it.

   `5e87234e` made it opt-in and stopped the summary reaching content, which left one
   question: should it exist? By this repository's own rule a producer with no consumer is
   **deleted rather than configured** -- a switch over something nothing reads is not
   configurability, which is also why it never entered `config_schema.py`. The only
   consumer anyone could name for a face count is itself a privacy inference, so
   reconnecting it is a proposal with its own threat model, not a restoration. The module,
   both call sites, the five metadata keys and both settings are gone.

   One detail from the removal is worth keeping: **OpenCV was never a declared dependency**.
   `detect_people_in_image` caught `ImportError` and reported `"unavailable"`, so detection
   ran only where something else had pulled `cv2` in -- a privacy-affecting default whose
   behaviour depended on an undeclared transitive package.

   `tests/security/test_faces_are_not_detected_at_ingest.py` matches the **library calls**
   (`CascadeClassifier`, `HOGDescriptor`, `detectMultiScale`, `haarcascade`,
   `face_recognition`, `mediapipe`) and the five field names, not the old module path, so a
   reimplementation under another name is caught. Both scanners were verified able to fail
   by dropping the deleted file back into `app/` **under a different filename** -- the rule
   this file records for the sensitive-content gate, applied to its own suite.

   **Still not covered, deliberately or otherwise**: names, street addresses, licence
   plates; no content-moderation/toxicity filter and no bias detection. Uploaded documents
   are never inspected — `app/services/documents/` calls nothing from `app/privacy/` — so
   chunks sit raw in ChromaDB, BM25 and on disk, and `mask_evidence` redacts at *read*
   time. That is defensible (it is the user's own document, in their own tenant, and they
   have to be able to read it back) but it means a scope-resolution bug exposes original
   text rather than redacted text. And `privacy_permission` inspects `request.question`
   only: the API persists the raw query into session history and feeds it back as
   conversation on the next turn, so input redaction is per-turn. Egress is still covered
   by the wrapper above; what makes this worth watching is `QUERY_REWRITE_WITH_LLM`, false
   today, which is what would let that history reach a retrieval query.

**Skills shape the answer** (wired 2026-08-31). The router picks one of nine skills per
query and `RouteDecision.skill` has always carried the choice, but nothing read it:
`SynthesizerAgentService` hardcoded `answer_with_citations`, and `skill_name` reached the
model as a bare header line with no content behind it.

`app/agents/synthesizer/skills.py` is the one place that decides what a skill means, and it
**selects** a template rather than adding one. `templates.py` already infers a *query type*
from the question by keyword and puts its template in the prompt; a parallel set of skill
templates would have put two competing answer shapes in front of the model. Skill and query
type answer the same question, and the skill is the better answer — an LLM read the whole
question, `infer_query_type` matches a keyword list. So:

- six skills have a shape of their own (`timeline_builder`, `web_fact_check`,
  `incident_response_playbook`, `cyber_attack_analysis`, `cyber_defense_hardening`,
  `pdf_text_reader`);
- `compare_entities` maps onto the existing `COMPARISON_TEMPLATE`, which means an
  LLM-detected comparison now reaches it even when the wording carries none of the keywords
  — the same "the route is an instruction, not a hint" reasoning as on the retrieval side;
- `answer_with_citations` and `ai_knowledge_assistant` state no shape and keep today's
  question-based inference, as does an unrecognised skill.

Every authored template teaches the internal `[E{k}]` marker, never `[1]`: `output_filter`
renumbers after DLP settles which citations survive, so a template teaching reader-facing
numbers would teach the model to invent numbering the pipeline then overwrites.
`tests/agents/synthesizer/test_skill_templates.py` checks the three sets partition
`VALID_SKILLS`, so a skill added to the router without guidance fails the suite.

**Citation-First Principle**: Factual claims must carry an inline citation during
generation. Two marker formats are involved and they are not interchangeable:

- `[E1]`, `[E2]` … are the **internal** evidence markers. `ContextBuilder` renders one in
  front of each excerpt (`app/knowledge/context.py::_render_item`), the prompts teach that
  form, and `normalize_answer_citations` allow-lists it, so `[E{k}]` always names an exact
  position in the evidence list.
- `[1]`, `[2]` … are what the **reader** sees. `output_filter`
  (`app/orchestration/langgraph/nodes.py`) rewrites the internal markers via
  `number_evidence_markers` and appends the numbered reference list, so entry *n* is what
  `[n]` in the text points at.

The rewrite happens in `output_filter` and nowhere earlier, because that is the first stage
that knows which citations survive DLP: a marker whose evidence the filter dropped is
removed rather than left pointing at nothing. It used to live only in
`SynthesizerAgentService.synthesize()`, which the LangGraph path never calls, so `[E1]`
reached the browser verbatim with no legend.

Numbering is by **first appearance in the answer**, not retrieval order, and two excerpts
that render as the same reference line (same `source`, same `page`) share one number.
`EvidenceBundle.items` comes back from `output_filter` in that same order, which is what
lets `RAGPipeline` set `PipelineCitation.marker` by enumeration.

`EvidenceRef.version` is optional on purpose, mirroring `EvidenceItem.version`: web results
and graph context are real evidence with no version to point at. Requiring one there meant
every marker aimed at them was silently dropped, so a web-routed answer returned no
citations at all and finished `degraded`.

**Self-RAG runs where the caller asks for it, and nowhere else** (2026-09-03).
`_run_self_rag_evaluation` in `app/api/routes/public/query.py` is the only Self-RAG there
is: it awaits `SelfRAGEvaluator` properly and is gated by the request's `enable_self_rag`.
There used to be a second one in `app/agents/rag/vector.py` -- a `_evaluate_retrieval` that
returned `{"enabled": True, "evaluated_count": N}` beside a comment saying the real
implementation would be async. It had never run: the agent's one construction site supplies
no `llm_client`, so the evaluator was always `None`; the branch was additionally gated on
`VectorRAGConfig.enable_evaluation`, default false; and `run_vector_rag` rebuilt the result
from five keys, dropping `evaluation` anyway.

Connecting it was never the option: the evaluator's methods are coroutines, `execute` is
synchronous and reached from `asyncio.to_thread`, and driving a coroutine from there is the
defect already fixed twice in this repository. It is deleted, along with the config field
`GET /api/advanced-rag/config` was reporting as `self_rag.enabled_by_default` -- a field
that gated nothing, reading `false` for the same reason the real switch does, which is why
nobody noticed. That endpoint now reports the request flag, and
`tests/api/test_advanced_rag_config.py` asserts each key follows the thing that gates it
rather than asserting a value.

**Dormant by design (2026-08-29)**: the following exist and are reachable but are
switched off on the live request path. Turning any of them on is a cost/latency
decision, not a bug fix — do not "fix" them by flipping the flag.

- **Fact verification and self-review**: `app/agents/synthesizer/service.py` calls
  `synthesize_answer(..., enable_fact_verification=False, enable_self_review=False)`.
  Fact verification is now switchable without a code edit
  (`ANSWER_FACT_VERIFICATION_ENABLED`, default false) **and works when switched
  on**: the synthesizer passes it the structured evidence directly. It used to
  rebuild source documents by regexing `[doc_id:page]` out of the rendered
  context -- a form retired when ContextBuilder moved to `[E{k}]` -- so it
  verified every answer against an empty list and reported perfect groundedness.
  With no source documents it now skips rather than passing vacuously.
- **Router confidence calibration**: `ENABLE_CALIBRATION` defaults to false, and
  turning it on now does something. The loop was closed on 2026-08-30:
  `_record_routing_outcome` (in the verifier node) feeds `record_routing_feedback`,
  which previously had no caller anywhere. Only outcomes *attributable to routing*
  are recorded -- retrieval finding nothing is the route's fault, retrieval finding
  plenty and the verifier approving is to its credit, and a degraded answer that
  had evidence is somebody else's failure and records nothing.
  `RouteDecision.raw_confidence` exists to carry the pre-calibration value that
  far; feeding the calibrated one back would train the calibrator on its own
  output. Accumulated outcomes live at `ROUTER_CALIBRATION_PATH` under `data/`,
  seeded once from the tracked `config/router_calibration.json`, and are flushed
  every 20 records -- the calibrator used to rewrite that tracked file
  synchronously on every request.
- **Clarification round caps**: derived from the number of fields each intent
  actually has questions for (`rules.py::_REQUIRED_FIELDS`), not hand-written.
  The old table said 7 for `rag_design`, which has four fields, so the cap could
  never be reached and the UI promised three rounds that do not exist.
- **Enhanced graph lookup**: `GRAPH_RAG_ENHANCED` defaults false, so the graph route uses
  `app/tools/graph/core.py::graph_lookup`. Until 2026-08-31 the switch was not dormant but
  *broken* — `_run_graph_rag_impl` required `retrieved_docs` to enter the enhanced branch and
  the one production caller had none, so all 495 lines of `app/agents/rag/enhanced_graph.py`
  were unreachable. It now works, and staying off is a cost decision: the enhanced lookup
  loops per entity (up to 5 neighbor queries + 3 path queries) where the basic one batches,
  so it trades roughly 3 Neo4j round-trips for up to 9 in exchange for better entity
  normalization, alias matching, quality-adaptive limits, and a low-quality skip that falls
  back to vector. Turning it on also turns on two-phase retrieval — see Retrieval Strategy.
  `ClarificationAgentService` advances the round when it *asks*; the session
  store used to be the only thing that advanced it, and only when the user
  answered, so a caller that re-asked without answering looped forever.

**Note**: Quality validation is controlled by `ExecutionPolicy`, not by per-profile
settings — see Pipeline Profile above.

### The first run creates an administrator

`scripts/create_admin.py` was the only way to get an account with the `admin` role, so
until 2026-09-08 a checkout had none: every `/admin/*` endpoint and all ten tabs of the
console were unreachable by anyone who had not read the documentation. That is not a
feature that is switched off, it is a feature nobody can find --
`app/services/auth/bootstrap.py::ensure_admin_account` now runs from the lifespan and
creates one when there is none.

Four decisions in it are the point, and each is a way this shape usually goes wrong:

- **No default password.** `admin/admin` is the first pair anything scanning the internet
  tries, and a credential in this repository is a credential in every checkout of it. The
  password comes from `ADMIN_PASSWORD` or is generated per installation.
- **It keys on "no *active* administrator", not "no users".** An installation where
  somebody registered an ordinary account first would otherwise never get one and would be
  locked out with no way in short of editing SQLite; and an installation whose only admins
  are *disabled* is in exactly the state this exists for, which a row-existence check
  misses. Recreating one on restart is a recovery path, not a way past authentication --
  whoever can restart the process can already read the database.
- **An existing account is never promoted.** If the chosen username is taken by a
  non-admin the bootstrap refuses and says so. Raising somebody's role because their
  username collided is privilege escalation triggered by a string. (Without the guard it
  is a bare `sqlite3.IntegrityError`, which is the shape somebody "fixes" by promoting.)
- **A weak `ADMIN_PASSWORD` is an error, not a fallback.** Generating a different one
  would leave the operator unable to sign in with what they set and nothing would say why.

**The generated password goes to stderr, never through `logging`.** `setup_log_capture()`
buffers records for the admin console's own log viewer, so a password logged there is
readable by every administrator added afterwards -- a wider audience than the one person
meant to see it. `describe_bootstrap` returns the block and the caller prints it;
`test_the_password_is_never_written_through_the_logger` pins it.

`ADMIN_USERNAME` and `ADMIN_PASSWORD` are read from the real process environment and are
**not** `Settings` fields, for the reason `NACOS_PASSWORD` is not one: a field can reach a
configuration endpoint. Both are in the `test_config_has_one_source.py` allowlist with
that reason, and a test greps `config/env/*` and `config/profiles/*` for `ADMIN_PASSWORD`,
because a key in a tracked layer looks exactly like a live setting.

**The lifespan skips this under pytest**, so a test run cannot write an account into the
developer's `data/app.db`; `tests/services/test_admin_bootstrap.py` (22) drives the
function directly, which is a better test than a side effect of starting an app. The
startup wiring itself was verified by running it: an empty database produced the banner
and one `admin` row, a second run produced nothing, and a username collision logged the
refusal and let startup continue.

`scripts/create_admin.py` stays, and now calls the same `ensure_admin_account` rather than
carrying its own copy -- two definitions of "what an administrator is" is how the two
drift. What it still does that a running server will not is reset a forgotten password.

Verified able to fail in four directions: a constant default password, promoting the
colliding account, keying on "any users at all", and logging the password each redden the
test that exists for them.

### Governed tool stack

`app/mcp/runtime.py::get_tool_stack()` builds the approval store, registry,
gateway and connector service **once per process**, lazily. Both the FastAPI
container (`app/api/deps/runtime.py`) and the RAG pipeline
(`ToolAgentService`, resolved at call time so `CoreCapabilities()` stays cheap)
resolve that one stack.

Sharing is a correctness requirement, not a performance one: `ToolRegistry`
mints an approval token into *its* `ApprovalStore` and
`POST /api/v1/connectors/approvals/{token}` redeems it from whichever store the
FastAPI dependency hands out. Two stores means a token that can never be
redeemed. Before 2026-08-30 the API built its own stack and the pipeline had
none at all, so every pipeline tool call returned "tool system not initialized".

`ToolAgentService` resolves the stack on first *use* rather than at
construction: `CoreCapabilities` builds it by `default_factory`, and eager
construction would demand `API_SETTINGS_ENCRYPTION_KEY` of every test and script
that touches capabilities. Do not inject it via `RAGPipeline(tool_agent=…)`
either — that sets `_uses_default_capabilities` False and rebuilds the LangGraph
workflow per request (~20ms of synchronous CPU on the event loop).

**Approval is resumed by replay, not by checkpoint restore** (2026-08-30). A
`write` tool returns `approval_required` with a token; the run finishes normally
and `PipelineResult.status` becomes `pending_approval`. The client confirms at
`POST /api/v1/connectors/approvals/{token}` and then **re-sends the same query
with `approval_token`**. That second run re-executes from the top and its tool
stage replays the approved call.

Replay rather than a LangGraph checkpointer, on purpose: re-running means
`privacy_permission` **re-resolves** the caller's access scope instead of
restoring one captured before the pause. Permissions can change while a human
looks at a confirmation dialog, and a checkpoint restore would have replayed the
stale scope silently. It also avoids a new persistence store, conversation-scoped
thread semantics, and TTL cleanup. The cost is one extra retrieval + synthesis,
only on the approval path. **The `checkpointer` parameter on
`OrchestrationEngine`/`build_workflow` is still never passed and this design does
not need it — do not assume that path works.**

Resume does **not** re-run tool selection: `ApprovalStore.approved_call` rebuilds
the exact call from the approval record. A model re-reading the same question is
not obliged to choose the same call, and the approval has to authorize the action
the user was shown.

`_call_fingerprint` no longer includes `execution_id`. It used to, which made a
token structurally unredeemable — every chat turn is a new execution, so the
retry's fingerprint could never equal the approved call's. Approval still binds
to one actor, is single-use, and expires in 5 minutes.

Before this the loop was broken in three independent places: the frontend
approved a token and then only cleared its panel, `OrchestrationRequest` had no
field to carry a token back, and the fingerprint could not match.

**Connector storage is persisted** (2026-08-30). `ConnectorMetadataRepository`
and `CredentialRepository` were process-local dicts, which was survivable only
while the tool path could not execute anything: a restart silently emptied every
user's integrations, and a connector configured on one worker was invisible to
the next. Both are now SQLite tables in `APP_DB_PATH`, following the store
pattern the rest of the app uses (own connection per call, schema on
construction) rather than a shared pool, which this codebase deliberately does
not have.

Both tables carry `owner_id REFERENCES users(user_id) ON DELETE CASCADE`, so a
deleted account cannot leave behind an encrypted secret. `create` relies on the
primary key rather than read-compare-write under a lock, which only ever made
the race single-process.

**The encryption key now has to outlive the process too.** Ciphertext is what
gets stored, so persisting it does not widen what a database read exposes — but
rotating or regenerating `API_SETTINGS_ENCRYPTION_KEY` turns stored credentials
from *absent* into *undecryptable*.

**A stored credential must be one its owner can take back** (added 2026-09-09).
Connectors could be created, listed, enabled, disabled and probed, and there was
no delete anywhere in the stack -- not on the router, not on
`ConnectorManagementService`, not on `ConnectorMetadataRepository` and not on
`CredentialRepository`. So an encrypted third-party secret, once handed over,
stayed: its owner could stop it being used and never remove it. Found by trying
to clean up a test connector after an end-to-end run, which is a fair sample of
how it would have been found in production.

`disable` is not the same thing and stays: stopping a suspect integration while
keeping the record of it is a real need. This is a new verb, `DELETE
/api/v1/connectors/{connector_id}` → 204.

**The credential is destroyed before the metadata, and which residue an
interrupted delete leaves is the whole design.** The two stores are separate
connections on the app database -- there is no shared pool here on purpose --
so the pair is not atomic. Metadata gone with the ciphertext left behind is a
secret nothing can name, which is a *worse* state than not deleting at all;
metadata left with the ciphertext gone is a connector its owner can see and
delete again. Both halves are idempotent so that retry works.

Two details in `tests/services/test_connector_deletion.py` (12) are worth more
than the endpoint. Both 404 tests assert the **message**, not only the status:
with no route registered, FastAPI answers that DELETE with its own 404, so
status alone passes on exactly the code they exist to reject -- the vacuous
assertion this file keeps recording, met here in a new place. And the ordering
above is pinned by making the metadata delete raise, because it is a choice
nothing else would state. Verified able to fail: all twelve redden against the
previous commit.

The reader-facing half is a delete control in `IntegrationsPanel`, behind
`ConfirmDialog`. It asks where disable does not, for the reason the memory
panel's "forget everything" asks: the server cannot show a secret back, so
there is nothing to undo it from.

Measured in a real browser through the same throwaway harness the memory panel
used -- real components, real cascade, real aurora, only `window.fetch`
replaced, deleted in the same change. Cancel sends no request and keeps both
rows; confirming sends exactly one `DELETE /api/v1/connectors/falcon_runbook`,
drops the row and reports it. **16 nodes checked with the panel open and 20 with
the dialog open, one failure at 2.08** -- the disabled connector's `Test`
button, the inactive-component exemption already recorded for this panel. The
destructive confirm is white on `rgb(189,16,16)`, 6.48. `__probe()` caught all
three planted nodes first, so the scanner was known able to fail.

**Two instrument failures on the way, and neither was an application defect.**
`computer`'s click missed because the pane's screenshot is scaled (a 952px
viewport rendered at 800px) while a `ref` resolves to *page* coordinates;
`document.elementFromPoint` at the button's own centre is what proved nothing
covered it. And fetching the auditor with `fetch()` returned the harness's
stubbed connector JSON, because the harness had replaced `window.fetch` -- a
`<script src>` bypasses it. Same rule as the `Return`/`Enter` and `shift+slash`
corrections: check the instrument before filing the finding.

### Upload storage

`store_uploaded_files` (`app/services/documents/dedup.py`) is the front door for user
documents, and three of its decisions outlive the request. The directory a file lands in
(`uploads_path/<owner_user_id>/`) is what document visibility falls back to for rows
indexed before owner metadata existed; the visibility it resolves is what the row is
indexed with; and the hash it computes is what stops the same file being stored twice.

Two rules worth keeping in mind before changing it. **Public needs an approval that is
exactly `True`** -- a missing answer is not a yes, and this is the last place a private
document can stop being private. And **an index row is not evidence that a file exists**:
`_existing_duplicate` re-hashes the stored copy before telling a request it already has
the file, because the index can outlive what it points at.

`tests/security/test_upload_storage.py` pins the refusals, which are the direction that
fails open.

### User Data Isolation

Retrieval is scoped, not just filtered afterwards (fixed 2026-08-30). Two properties
carry it, and both are pinned by `tests/security/`:

- `privacy_permission` (`app/orchestration/langgraph/nodes.py`) resolves the caller's
  `AccessScope` and **rewrites `request.source_scope` from it**, so no later stage can
  be handed a wider range than the resolver authorized — whatever the API layer passed.
  This is why `pipeline_contract.py` may still pass `allowed_sources=None` harmlessly.
- `similarity_search` fails closed: a missing `allowed_sources` raises rather than
  searching every tenant's corpus, and an *empty* one returns nothing. Those two cases
  must stay distinct — collapsing them is what previously turned "this user has no
  documents" into an unrestricted search.

`evidence_is_authorized` (`app/privacy/dlp.py`) remains the output-side check. `web` and
`tool` evidence is exempt (not user documents); `memory` is checked against the
`memory://{tenant}/{user}/` namespace its store already enforces, not against
`allowed_sources`, which only ever holds document paths.

Counts of scope-dropped evidence are logged, never returned: they would tell a caller
how many documents *other* tenants hold on a topic.

An **empty** document scope (a user who has uploaded nothing) and a **missing** one are
different states and must stay so. Empty drops the document-backed retrievers but keeps
web — web results are not documents — and returns quietly; missing raises. Collapsing
them in either direction is a bug: one way silently removes web search from every new
user, the other turns "a caller bypassed the resolver" into a result that reads as "no
matches found". `KnowledgeOrchestrator._retrieve_source` skips only
`vector`/`bm25`/`graph`/`wiki`/`multimodal` on an empty scope; `RAGAgentService.retrieve`
matches that list rather than short-circuiting ahead of it.

The store adds a second, independent check: `similarity_search` takes an `OwnerScope` and
requires the chunk's own `owner_user_id`/`visibility`/`tenant_id` metadata to match, not
just its `source`. Source paths are *derived* from the visibility rules; owner metadata is
written independently at ingest, so requiring both narrows what a wrong source list can
reach. **This means chunks indexed before ingest wrote owner metadata are invisible once
the clause is on — `$eq` does not match an absent key (verified on chromadb 1.5.9). Reindex
any pre-existing store before deploying.** Every `similarity_search` call site must pass an
owner; `tests/security/test_no_unrestricted_retrieval.py` enumerates them via AST and keeps
the one genuinely caller-less site in a documented allowlist -- the offline evaluation
harness, which has no request and no user. A partial guard would be worse than none. The
second entry was `candidate_collection`'s default `vector_fn`, an ownerless
`similarity_search` kept out of reach by every live caller injecting an owner-bound
partial; `vector_fn` is required and defaultless now, so the module no longer reaches the
store at all and the entry is gone rather than reworded.

**The owner must survive every hop, not just the call site** (fixed 2026-08-30). The AST
guard only sees direct `similarity_search` calls, so it passed the whole time the graph
route was reaching the store through `run_graph_rag → _fallback_to_vector_rag →
run_vector_rag → hybrid_search_with_diagnostics → _safe_similarity_search`. Every hop wrote
`owner=owner`, which satisfies an AST check — but `_fallback_to_vector_rag` declared
`owner: OwnerScope | None = None` and two of its three callers relied on that default. Neo4j
is optional and an empty graph result is routine, so the *common* fallback searched with the
source filter alone and no ownership clause.

The fix is a shape, not a patch: on every function between a request and the store, `owner`
is **keyword-only with no default**, so omitting it is a `TypeError` rather than a silent
widening. `similarity_search` itself is the one exemption — it is where "no owner" is
interpreted. Two guards keep it that way: `test_no_retrieval_helper_defaults_its_owner_away`
(no `owner=None` default anywhere upstream) and
`test_no_module_passes_a_null_owner_without_saying_why` (writing `owner=None` requires an
`OWNERLESS_CALL_SITES` entry). `hybrid_search()` and `_collect_candidates()` were deleted in
the same pass: both were callerless and neither could take an owner, so each was a
ready-made way back to an ownership-blind search.

Documents are addressed by `document_id`, not filename: two users routinely hold a
`report.pdf`, so `/documents/{filename}` refuses whenever the name is ambiguous and
`/documents/by-id/{document_id}` is the form the frontend uses. A `?source=` query
parameter *narrows* the candidates a filename resolves to — it must never select one on
its own, which is what let an admin act on a file they could not even list. "No such
document" and "not yours" both return 404 on purpose: distinguishing them discloses that
someone else's document exists.

**Chinese tokenization is jieba plus character bigrams** (fixed 2026-09-04).
jieba's dictionary used to be the only vocabulary: single-character tokens were
dropped -- they carry almost no signal alone -- so a word the dictionary does not
know produced *nothing*. `年假` splits into two single characters, so it vanished
from the query and from the document alike and could never match. Measured over 30
realistic domain terms only one behaved that way, but it is a silent *total*
failure and the affected set is unpredictable.

The more common failure is worse than a miss: jieba emits a sub-word, and the
sub-word gets used as if it were the word. `陪产假` (paternity leave) tokenized to
exactly `产假` (maternity leave) -- an identical token set, so BM25 could not tell
them apart, and a query about one ranked the other first. That is a wrong answer,
not a missing one.

Bigrams over each CJK run fix both without a dictionary, and are added *alongside*
jieba's tokens so a known word keeps its whole-word match. Runs stop at
punctuation. Measured on `config/eval/`: MRR 0.9062 -> 0.9688.

**What it does not fix, and cannot**: asking about `产假` still ranks the `陪产假`
document first, because `产假` is genuinely a substring and BM25 rewards matches
without penalising a document for extra terms. That is the boundary of lexical
retrieval -- the production pipeline fuses BM25 with vector search, which the
BM25-only evaluation harness deliberately does not. It is pinned as
`KNOWN_LEXICAL_LIMITS` in `tests/evaluation/test_retrieval_metric.py`, with the
rank asserted exactly so an improvement fails the test as loudly as a regression.

BM25 keeps one prebuilt index per access scope (`_load_scoped_bm25`, LRU), and separates
matching from ranking: a document is a candidate if it shares a term with the query, and
BM25 only orders the candidates. Do not reintroduce `score > 0` as the membership test —
BM25 IDF is negative for a term present in most documents, so in a small scope (one chunk,
now a routine case) every term scores below zero and matching documents get dropped. A
negative `bm25_score` in the output is normal and harmless: RRF fuses on rank, not score.

### Audit log vocabulary

Action names have one definition, `app/services/security/audit_actions.py::AuditAction`
(added 2026-09-03). Forty-nine names are written at some seventy call sites across
`app/api`, read back by string comparison in `app/services/runtime/runtime_ops.py`, and
listed again in the admin console's filter — three lists that had to agree, with nothing
checking that they did.

**Unlike the permission vocabulary next door, a divergence here fails silently**, and two
had already happened when the enum was introduced. The console offered
`admin.user.create`, `admin.user.password_reset` and `admin.user.approval_token_reset`
against a backend that writes `create_admin`, `reset_password` and
`reset_approval_token`; the filter is a substring match, so four of its sixteen options
(`query.stream` was the fourth) could only ever return nothing. And `build_ops_alerts`
averaged the grounding ratio over rows with action `query.run`, which nothing has ever
written. A counter that matches no row reports zero and a filter that matches no row
reports "no results" — neither looks like a defect to anyone.

`StrEnum`, so members are strings: `sqlite3` and `json.dumps` both see `"auth.login"` and
no call site changed behaviour. What changed is that a name that does not exist is an
`AttributeError` at import.

`tests/security/test_audit_action_vocabulary.py` scans every module in `app/` for a
literal equal to any member — which is how twelve *positional* call sites in
`admin/users.py` turned up, passed to `handle_service_exception` and
`check_self_modification` rather than to `_audit` — and checks the console's list against
the enum, and that the list is declared once. It was declared twice in `frontend/src`,
identically, which is how the first divergence went unnoticed.

**The two `query.*` actions are written only when a query is *refused*.** No successful
query is audited, which is why nothing carries a per-answer quality metric — see Answer
quality telemetry under Important Notes for where that goes instead.

There were three until 2026-09-06. `query.source_scope` was removed with its only writer,
an adapter in `api/deps/documents.py` that imported a module `4994d7f3` had deleted — so
the console offered a filter that could only ever return nothing, which is the defect this
section opens with, reached from the opposite direction: not a name that disagreed with the
backend, but one both ends agreed on with no row behind it. The direction the existing
tests checked was console ⊆ enum, and that passes on a member nothing writes;
`test_every_action_in_the_vocabulary_is_named_by_some_module` checks the other.

### Knowledge Agent and retrieval execution

**The Knowledge Agent is not an agent.** `app/orchestration/capabilities.py` constructs
`KnowledgeAgentService()` with no `decider`, so `_rule_strategy` -- a set of regexes over
the question plus the route's hints -- is the only path that runs in production. The
`StrategyDecider` seam is real and `_bounded` polices what one would return, but nothing is
plugged into it. That is a defensible design (fast, deterministic, auditable); it is
recorded here because the name promises otherwise and the next reader will go looking for
an LLM that is not there.

Source selection and retrieval execution are separate jobs, and since 2026-08-30
they are separated properly. `KnowledgeAgentService.decide` picks the sources;
`RAGAgentService.retrieve(request, route, plan, strategy, scope)` runs exactly
that strategy through `KnowledgeOrchestrator` with `build_default_adapters()`.

Before this, `RAGAgentService` built a strategy of its own -- always vector+BM25,
graph on two routes, `rewrite=False` -- which silently overrode the one the
Knowledge Agent had just produced. Three consequences, all fixed together:
`memory`, `wiki` and `multimodal` were unreachable on the chat path however the
Agent chose them; query rewriting never ran; and a verifier retry re-ran the
identical search, because the retry query lives in the strategy.

**The route is an instruction, not a hint.** `_knowledge_hints` translates each
route into the sources it implies and `KnowledgeAgentService` includes them
unconditionally. Consulting only keywords is what let a `graph` route degrade to
vector+BM25 whenever the wording carried no relationship words.

**Web has two independent authorizations.** The router choosing the `web` route
*is* permission to search the web; `use_web_fallback` additionally allows a
freshness-driven web search on routes that did not ask for it. Requiring the flag
for both meant its default (False on every chat request) removed web search from
the web route itself.

There is one retrieval path. `KNOWLEDGE_ORCHESTRATOR_ENABLED` used to switch
between two, and the default sent every request through the branch that
discarded the strategy.

`FinalAnswer.evidence` is the full authorized retrieval set and
`FinalAnswer.cited_evidence` is the cited subset in citation-number order. They
were the same list, which made `PipelineResult.contexts` and `citations`
duplicates and hid every retrieved chunk the model chose not to cite.

### Multi-turn follow-ups

A follow-up question is completed before it is retrieved on, not after (wired 2026-08-31).
`request.conversation` used to reach only the synthesizer and the tool selector, neither of
which retrieves: the router saw only `request.question`, the Knowledge Agent used it
verbatim as the retrieval query, and `build_rewrite_queries` took a query with no history.
So "成本呢？" ran a vector search on those three characters and the synthesizer had to
answer from evidence fetched for the wrong query — a failure that reads as poor retrieval.

The completion happens in the rewrite step the repository already had:
`KnowledgeOrchestrator._rewrite_once` → `build_rewrite_queries` → `_llm_rewrite`, which was
missing only the conversation argument. With history present the rewriter switches to a
standalone-question prompt; with none it keeps its original wording-only prompt, so a first
turn costs nothing new. `QUERY_REWRITE_WITH_LLM` still gates the LLM call and still defaults
false — turning it on is the cost decision, and it is now a switch that does something (see
Caller deadlines: `_llm_rewrite` could not run at all before `request_context` was opened
for the workflow).

**The original question always survives.** `_with_queries` merges it in ahead of the
variants, so a wrong completion adds a bad query rather than replacing the good one — the
model is guessing what the user meant and can guess wrong. `primary_query` (what reranking
scores against) is read before the merge and stays the question as asked.

`enable_context_tracking` finally has a meaning, and it is enforced in one place per
consumer: `RAGAgentService.retrieve` decides what retrieval may know about the session, and
`SynthesizerAgentService.synthesize_candidate` decides what generation may. Off means
neither sees it.

**`app/services/context_management.py` is deliberately not on this path.** Those 642 lines
implement the older rule-based alternative (pronoun → entity), and it decides a question
needs resolving by substring-matching a fixed pronoun list. Both directions fail on ordinary
Chinese: the most common follow-up shape drops the subject entirely, leaving nothing to
match ("成本呢？"), while 那/这 are substrings of ordinary words and particles, so a
self-contained question gets a stale entity substituted into it ("那延迟呢"). It also carries
a hardcoded company gazetteer and a process-local per-session dict. It keeps its one real
reader, the session-export endpoint, where an entity and topic list is a reasonable product;
`tests/knowledge/test_followup_rewriting.py` pins both failure directions so reviving it
stays a deliberate choice.

**The API sends turns, not a blob.** `POST /api/advanced-rag/query` used to collapse the
session into one `system` message holding a pre-rendered memory block. Synthesis could live
with that; rewriting cannot, because completing a follow-up means knowing what the previous
turn asked. The block still leads the sequence — it also carries the long-term memories the
raw turns do not — and `_render_turns` skips it when building the rewrite prompt so the same
rounds are not shown twice in two formats. One consequence of the old shape: the
`max_turns=12` bound in `_render_conversation` was dead, because there was only ever one turn.

### Long-term memory is the user's data, and had no page

`_promote_long_term_memory` runs on every answered query and `build_memory_context` feeds
the selected memories back into the next one, so this system accumulates memories about a
person and uses them to shape later answers.

**Retrieval of those memories could not see Chinese at all, and then could not
rank** (both fixed 2026-09-09). `TOKEN_PATTERN` was written doubly escaped, and
in a RAW string `\u4e00` is a literal backslash followed by `u` -- so the second
alternative was a handful of ASCII punctuation rather than a CJK range. Measured
on the shipped pattern, `"我喜欢向量检索"` tokenized to `[]`. The BM25 branch is
guarded by `if query_tokens and any(tokenized)`, so a Chinese question skipped
ranking entirely and fell through to **the two most recent memories regardless of
relevance** -- and a Chinese memory could not be matched by an English question
either, since its own tokens were empty. Every string literal in the tree was
checked by parsing it and inspecting the VALUE rather than grepping the source
(twenty other regexes carry `一` correctly); this was the only one. Third
time this file has recorded a shell heredoc eating a backslash.

**Fixing it exposed the second defect, because the English test then failed.**
With two memories, BM25 IDF is zero for a term present in half the corpus, so the
relevant memory and an unrelated one both scored exactly 0.0; the membership test
was `score > 0`, so both were discarded and retrieval fell back to recency.
`LONG_TERM_TOP_N` is 5, so a memory set is small by design and this was the
normal case. Membership and ranking are separate questions now -- a memory is a
candidate if it shares a token with the query, and BM25 only orders the
candidates -- which is the rule this file already gives for the main BM25 path.
`tests/services/test_memory_tokenizer_matches_chinese.py` (11) pins both, plus a
recurrence guard and a test that the guard can fail; 7 of the 11 redden against
the shipped code. Until 2026-09-08 **nothing in the frontend
named them** -- a full-text search of `frontend/src` for `memor` returned no API call at
all.

**Not every answer becomes a memory, and that is worth knowing before reading the store.**
`MemoryResolver.propose` looks at the *question*, not the answer, and keeps it only if it
matches one of four patterns -- `记住`/remember, `喜欢`/prefer, `提醒我`/remind me,
`我是`/`I am`/`my X is` -- which is what makes the four `kind` values (`explicit_remember`,
`preference`, `task`, `stable_fact`) mean something. It also refuses anything
`inspect_text` finds PII in, so a memory is never a redaction hole. What is stored is
derived from the user's own words, which is exactly why they have to be able to read it
back.

**Two endpoints existed and neither could do the job, for the same reason.** Both treated a
user-scoped record as though it were session-scoped:

- `list_long_term` returns `long_term_ids`, which `_recompute_long_term_ids` caps at
  `LONG_TERM_TOP_N` (5). It is a **working set** -- what one conversation will be given --
  and it merges the `_global` pseudo-session's rows in, so the five differ by which session
  asked. Measured on ten promotions: **nine stored, five listed, and a different five from
  `_global`**. The two carrying a desk location and a team codename appeared in neither
  session's list.
- `delete_long_term` searched only the payload of the session it was called on, while the
  list it answers merges the global set into every session. So it returned **404 for rows it
  had just returned**. Of the nine, a session could list five and delete three.

`MemoryStore` now has `list_all`, `forget` and `forget_all`, all of which walk **every**
payload under the store's directory, and `delete_long_term` delegates to `forget` --
validating the session id and then deliberately not using it to narrow the search.

**The half-delete is the failure worth remembering.** A candidate is held twice, in the
global payload and in the session that promoted it, and `list_long_term` reads both.
Dropping either copy alone leaves the memory listed *and still in the prompt*, so "deleted"
would report success and change nothing the reader can see.
`test_forgetting_removes_a_memory_from_the_prompt_as_well_as_the_list` pins it, and was
verified able to fail by reducing `forget` to the global payload alone.

`GET /api/v1/memories`, `DELETE /api/v1/memories/{memory_id}` and `DELETE /api/v1/memories`
are the record. Every handler resolves the store through `_memory_store_for_user`, which
keys it on tenant and user id, so an id in a URL names nothing outside the caller's own
directory -- there is no row for it to reach rather than a check that refuses to reach one.

**An expired memory is returned marked `active: false` rather than hidden.** It no longer
reaches the model but it has not gone anywhere; omitting it would report less held than is
held, and would leave no way to remove it. `_expired` became
`memory_is_expired(expires_at)` and takes the stored timestamp rather than a `MemoryItem`,
so the store asks the resolver's own question instead of carrying a second definition --
which matters because the store holds rows `memory_item_from_row` refuses, the legacy
shapes with no `kind`.

`forget_all` counts **distinct ids, not rows**: a memory is normally held twice, and
telling somebody who was shown nine that eighteen were deleted reads as data they were
never told about.

The reader-facing half is `features/memory/MemoryPanel.tsx`, a section of the settings
drawer beside Integrations rather than its own destination -- the same reasoning that
declined to build the prototype's separate Integrations button. Two details in it are not
taste:

- **The kind label is a switch of literal `t()` keys**, not an interpolated one, because
  `i18n/locales.test.ts` scans for literal calls; an interpolated key is invisible to it and
  a missing locale entry then renders English forever, silently.
- **The fetch effect must not depend on `t`.** react-i18next hands back a new `t` whenever
  the language changes, so a fetch keyed on it re-runs for a reason unrelated to the data --
  and under any `useTranslation` that does not memoize, it is an unbounded render loop
  rather than an extra request. That is not hypothetical: the first version of the test
  mocks a fresh `t` per render, and three vitest workers reached 1.8-3.4 GB with **no output
  at all** before being killed. The tell was the absence of output, not an error. The
  fallback wording is resolved at render time now, where it belongs.

**Stored memories reach an answer by two independent routes, and a fix checked against one
of them is half a deletion.** `build_memory_context` renders them into the prompt through
`list_long_term`; the `memory` retrieval source returns them as *evidence* through
`GBrainLongTermMemory.search`, which reads `list_global` instead -- a provider facade over
the same store, keyed by `memory_base_dir` on the same tenant and user. Both are tested,
and reducing `forget` to the session payload alone reddens both. There is exactly one
writer on the request path (`_promote_long_term_memory`) and these two readers;
`GBrainLongTermMemory.upsert`/`expire` have no caller in `app/` but touch the same store,
so there is no shadow copy anywhere.

**Deleting a conversation does not delete what it taught, and that is now pinned as a
decision rather than left as an accident.** `HistoryStore.delete_session` unlinks the
transcript and nothing else; a promoted memory lives in the `_global` payload precisely so
it outlives one thread, which is the design -- "my timezone is UTC+8" is a fact about the
person, not about where they mentioned it. That is defensible *only* while the person can
see and remove it, so
`test_deleting_a_conversation_does_not_delete_what_it_taught` asserts both halves
together: the memory survives, and it is still listed and still removable. Before this
change it survived with no remedy.

**An expired row is de-emphasised by its ground, never by `opacity`.** The first version
dimmed the whole row with `opacity-70`, which is the trap this file already records from
the other side: `opacity` composites the entire subtree and never appears in
`getComputedStyle().color`, so an audit walks straight past it. Measured, `--text-muted`
goes from 5.56 to **2.97** under it -- failing AA on the kind label, the expiry badge and
the date of every expired row. `bg-surface-muted` moves nothing (5.28), and the badge is
what reaches a screen reader anyway, which `opacity` never did.

That assertion is checkable without a browser, and the first attempt at it was **vacuous**:
a backslash-b written through a shell heredoc reached the file as a literal backspace, so
`not.toMatch(/<0x08>opacity-/)` could not fail. It matches class *tokens* now
(`className.split(" ")`), and was verified by putting `opacity-70` back. Worth the note:
a regex that silently stops matching is the same defect as a filter option nothing writes,
and `cat -A` is what showed it.

**Measured afterwards in a real browser and the calculation held**: the expired row
computes `rgb(250,249,247)` at `opacity: 1`, and the panel's worst node is **5.28**
(`--text-muted` on `--surface-muted` -- the description, the `Fact` and `Expired` badges,
and the dates), against 2.97 for what `opacity-70` would have produced. 32 nodes checked,
zero failures, and the three skipped were the harness's own header rather than the panel.

**Measuring it needed a harness, and the harness found a second finding the calculation
could not have.** The drawer is behind authentication, so the panel was rendered by a
temporary `harness.html` + `harness.tsx` at the frontend root -- the real components, the
real `styles/main.css` cascade, the real aurora ground and the drawer's own wrapper
markup copied from what is now `SettingsDrawer`, with only `window.fetch` replaced. On the first run the
audit **skipped** the description text: the panel body was `bg-surface-muted/60`, and an
alpha tint over a `glass-panel` over a gradient has no background the walk can resolve.
It is opaque now, which is the same remedy `--success-surface` exists for. A skipped node
is the one number that separates "clean" from "did not look", which is why the count is
reported rather than the failures alone.

What a harness like that proves and does not: resolved colour, layout and interaction are
real, because the CSS and the components are. Anything about the surrounding signed-in
page is not, and the drawer opening from the top bar was never exercised. Delete it in the
same change -- a fixture left in `frontend/` is a second entry point Vite will happily
serve.

`tests/services/test_long_term_memory_record.py` (27) and `MemoryPanel.test.tsx` (10). Each
was verified able to fail: restoring the shipped `delete_long_term` reddens the
cross-session deletion test; reducing `forget` to the global payload reddens two, and
skipping the global payload instead reddens four including the retrieval one; capping the
panel's list at five reddens four; removing the guarded payload read reddens the corrupt-file
test; and ignoring the confirmation on "delete all" reddens one.

**The two session-scoped endpoints keep their job and now say what it is.** Their
docstrings name themselves as the working set and point at `/api/v1/memories`, because the
next person to build a "what do you remember about me" screen will find them first -- they
are the ones with `memories` in the path. The command palette does not get an entry of its
own either; the settings item's `value` carries the drawer's section names instead, so
searching "记忆" or "memory" reaches it without inventing a second name for one
destination.

**Prompt version history is the other end of the same audit and is deliberately not built.**
The backend serves `GET /prompts/{id}/versions` and the approve/rollback pair; the frontend
prompt library calls only `/prompts`, `/prompts/check` and `/prompts/{id}`, so a prompt
edited badly cannot be rolled back from the UI. That is an ordinary missing feature. The
memory gap was not: it was stored personal data with no way to see or remove it.

### Knowledge graph extraction

**A triplet's confidence now says how it was produced** (fixed 2026-09-04), and until it
did, the graph route was serving invented relationships as evidence.

`extract_graph_triplets` stamped `confidence=0.7, method="legacy"` on *every* triplet
regardless of extractor, so `filter_triplets(min_confidence=...)` could not tell an
LLM-extracted relation from a regex-chained one and its threshold was inert. What it was
failing to filter matters: `extract_triplets_rules` does not find relations. It takes the
ten most **frequent** `ENTITY_PATTERN` matches -- and that pattern matches any 2-12
character CJK run, so in Chinese it matches nearly every word, including the "系统/模块/功能"
the LLM prompt explicitly excludes -- then pairs them **by adjacent frequency rank**, which
is an artefact of sort order, and labels every pair in a chunk with one relation keyed off
the whole chunk's wording.

And it was the default path, not an edge case: `MODEL_BACKEND=local` is what a fresh
checkout runs, the offline stand-in cannot emit the required JSON array, and
`extract_triplets` fell through to rules on every chunk.

`LLM_TRIPLET_CONFIDENCE` is 0.7 (today's effective value) and `RULE_TRIPLET_CONFIDENCE` is
0.25, below every shipped `graph_min_confidence` (`app/services/parser_profiles.py`:
0.55 / 0.6 / 0.65 / 0.75 -- **not** `Settings` fields).
`test_every_shipped_parser_profile_threshold_excludes_rule_confidence` pins that coupling,
which is otherwise invisible across two files. Three method values, because "this
deployment configured rules" and "this deployment's LLM is broken" were previously
indistinguishable: `llm`, `rules`, `rules_llm_fallback`.

**So an installation with no working LLM now writes zero triplets**, which is the truthful
number and must not be silently zero: `_triplet_rows` counts per method,
`ingest_paths` reports `triplets_discarded_low_confidence` and `triplet_methods`, and
`_insert_triplets` logs at INFO when everything was discarded, naming the threshold. A
graph route that quietly goes empty otherwise reads as a retrieval problem rather than a
configuration one. Deliberately *not* added: a `GRAPH_RULE_TRIPLET_CONFIDENCE` setting --
a knob whose only purpose is re-enabling a path judged to be fabrication is a knob for
turning fabrication back on. Lowering the profile thresholds was considered and rejected
for the same reason.

**There is no safe automatic migration for graphs already written, and none should be
attempted.** `batch_upsert_triplets` writes `confidence_max/count/avg` and **no `method`
property at all**; `graph_lookup` never reads confidence (it is write-only); and every
existing edge carries exactly 0.7, because both the old stamp and the client's own
normaliser default to it. So 0.7 is not a marker of junk, it is what everything looks like,
and `_write_graph_triplets` has no delete path so a reset reingest only adds edges beside
the old ones. The operator step is explicit:

```cypher
MATCH ()-[r:RELATED]->() DELETE r
```

then reingest. Neo4j is optional and empty on most installs.

**One read-side mitigation applies to existing graphs with no migration.**
`infer_relation` returns `RELATED_TO` whenever no keyword matched, making it the most
common relation in any graph built without an LLM -- and `_NOISY_RELATIONS`
(`app/tools/graph/core.py`) contained `"related"` but not `"related_to"`, so those edges
scored 0.6 and survived the filter that exists to drop exactly them. Adding it drops them
at read time on the next query. Its limit is worth stating: `infer_relation` also emits
`DEPENDS_ON`/`INCLUDES`/`USES`/`STORES_IN` on keyword hits, and those still survive.

### Multimodal retrieval

`multimodal` is a retrieval source the Knowledge Agent selects on visual or
tabular wording (`_VISUAL_QUERY_PATTERN` in `app/agents/knowledge/service.py`).
Until 2026-09-03 it was selected and returned nothing, every time, for three
independent reasons: `_retrieve_text` queried a collection named `text_chunks`
where the real one is `local_rag_collection`, so it logged a traceback per query;
`image_descriptions` and `table_summaries` were written by methods with no
caller; and the source spent a retrieval slot -- one the planner can otherwise
give to `web` -- to return nothing on exactly the questions it exists for.

**Ingestion is the producer now.** `_index_images` and `_index_tables`
(`app/services/documents/ingest.py`) run inside `ingest_paths` and report
`images_indexed` / `tables_indexed` in its result.

**Images** are indexed with whatever was actually read out of them -- the
loader's description or OCR text, or `ocr_image_bytes` run here when the loader
left it bare. An image nothing could read is skipped rather than indexed with the
reason: "Tesseract executable not found" as retrievable evidence is worse than
the image being absent.

**The vision caption is read from metadata, not from the rendered block** (fixed
2026-09-04), and that distinction is the whole of it. `ocr_image_bytes` renders the
scene caption, the people summary and the OCR result into one `page_content` and marks
a failed OCR with `[image_ocr_error]`; `_readable_image_text` discarded the entire
string whenever that marker appeared. Correct for the diagnostic, and it took the
caption with it -- *precisely* in the case a vision model exists for: a photo, a
diagram, a chart with no extractable text. With `IMAGE_CAPTION_ENABLED` on and
Tesseract missing, the model produced a perfect description and the image was indexed
as nothing at all, silently. `metadata["image_caption"]` carries the raw caption and
never holds a diagnostic, so reading it separately keeps both properties. It is
de-duplicated against the rendered block, which also contains it on the success path.

Note what this does *not* turn on: `IMAGE_CAPTION_ENABLED` still defaults false, and
captioning still needs a vision model. The fix means that switching it on now does
something on the images that need it most.

**Tables are indexed whole, and that is the point of them.** The chunker splits
by size and knows nothing about tables. Measured on a 40-row table: seven child
chunks, and *only the first carries the header row*. Parent expansion does not
rescue it either -- the second parent holds sixteen rows and no header. So a
question about a row in the middle retrieves `| Region-30 | 130 | 230 | 330 |`
with nothing to say which column is which, and the model answers from position.
It does not fail; it is confidently wrong. `_table_from_markdown` reads the
header and body back out of the pipe table the loader rendered, so `headers` is a
header again.

**A chunk's entity metadata was different every time it was ingested** (fixed
2026-09-06). `extract_entities` (`app/ingestion/chunking/metadata.py`) built each
list as `list(set(matches))`, and set iteration order over strings depends on
`PYTHONHASHSEED`, which Python randomises per process. Three of the five lists are
then truncated — acronyms and numbers to five, URLs to three — so it was not the
order that moved but the *content*: measured on one paragraph, seed 0 stored
`['API', 'SSL', 'SSH', 'HTTP', 'DNS']` and seed 1 stored
`['SSH', 'HTTP', 'TLS', 'CDN', 'DNS']` for the same text. `_first_distinct` keeps
order of appearance, which is deterministic and also makes the truncation mean
"the first five in this chunk" rather than "an arbitrary five".

It surfaced while characterising `split_documents_enhanced` for the refactor
below: two runs of the *unmodified* splitter produced different output. Worth
knowing as a technique — a refactor's own before/after diff is the cheapest
non-determinism detector this repository has, and it found something no test was
looking for. `tests/ingestion/test_entity_extraction_is_deterministic.py` spends
two subprocesses to pin it, because an in-process assertion cannot vary the hash
seed and asserting an expected order proves determinism only by construction.

**`split_documents_enhanced` was the highest cognitive complexity in the project**
(58 against a threshold of 15, `python:S3776`) until 2026-09-06, and almost all of
it was nesting: three loops deep, so every `if`, `or` and ternary inside paid the
depth as well as itself. Split into `_split_document`, `_split_parent`,
`_parent_id`, `_neighbours`, `_splitters` and `_document_identity`, verified
byte-for-byte over a ten-document corpus rather than by argument.

**Estimating cognitive complexity by hand does not work, and the first attempt at
this refactor proves it**: `_split_document` was judged "about 10" by reading and
measured 16, so a refactor of the project's worst finding would have shipped
leaving a new one. Sonar's number is only available after a push and an analysis,
which is far too slow a loop — the way to check locally is to implement the
scoring rules and validate the implementation against findings whose Sonar values
are already known (58, 35, 28 and 21 were available from the 2026-09-06 analysis,
and a calculator reproducing all four is worth believing about a fifth). Two properties the nesting hid are now pinned in
`tests/ingestion/test_splitter_chunk_indices.py`, because both look like tidying:
a blank chunk is **skipped but still occupies its index**, so `parent_index`,
`child_index` and the totals given to `enhance_chunk_metadata` are positions in the
splitter's output rather than in the kept subset; and `_neighbours` hands the
enhancer the **raw** neighbouring chunks while the chunk being described is
stripped, which are different strings whenever a chunk begins or ends on
whitespace.

**A chunk knows which section it came from** (closed 2026-09-06; it was an open
gap from 2026-09-05). The same size-only splitting costs headings as well as table
headers, and worse: the separator list splits *at* a heading, so measured on one
heading over forty sentences, chunk 0 was the 26-character heading alone with no
body to support, and the six chunks holding the answer carried no word saying what
they are about. `SmartChunker` (483 lines, `app/services/multimodal/`) was aimed
exactly here and was never constructed anywhere, so none of it ran. It was
**deleted rather than connected**: it read PDFs only through `fitz` where the
loader handles many formats, it had no notion of the parent/child pair retrieval
expands through, its `DocumentChunk` is not the type the index takes, and
`_split_section` ended with `# For simplicity, add all to first chunk` --
reproducing the table defect described just above, with a comment admitting it.

The idea outlived the implementation, recorded as `xfail(strict=True)` in
`tests/ingestion/test_chunk_section_headings.py` so that the day headings survived
chunking the suite would fail until someone removed the marker. **That is exactly
what happened**: the behaviour landed, the marker turned into an `XPASS(strict)`
and failed the suite, and it came off. Worth noting as a technique — a strict
xfail is a claim that fails loudly when it stops being true, where a sentence in a
plan just goes stale.

What landed is deliberately smaller than `SmartChunker` was. **Chunk boundaries are
unchanged**: the splitter still cuts by size and `_heading_scope` *carries* the
last heading seen onto the chunks that follow, in `metadata["heading"]`. Putting
the heading back into `page_content` would change every chunk's embedding and every
stored offset; a metadata key is additive, and verified so — over a ten-document
corpus the only difference is the new key, with chunk text and every other field
byte-identical. Splitting *by* section is a larger change with its own trade-offs
and was not made.

**`detect_heading_level` raised on a blank line**, found while wiring this up. Its
title-case rule reads `line[0]` after stripping, and `extract_document_structure`
calls it on every line *before* checking whether the line is blank — so the
structure pass blew up on any document containing one, which is nearly all of them.
Latent rather than shipping only because `PDF_ENABLE_STRUCTURE_ANALYSIS` defaults
false; and it would not have looked like a crash if switched on, because
`load_pdf_advanced` catches per page and keeps the *original* document, so formula
enrichment and coreference resolution would have been discarded along with the
structure and all three switches would have looked like features that did nothing.

One definition of "what is a heading" serves both callers, `section_headings`, and
it is **liberal on purpose**: measured over 415 lines of corpus and README text it
flagged 50, of which 45 were genuine markdown headings and the five it was wrong
about were ordered-list items and one all-caps diagram line. A chunk's `heading` is
"probably the section this came from", not a key. It is also **Latin-script only** —
a bare Chinese section title matches none of the four rules, so a Chinese document
without `#` markers gets no headings on its chunks. `tests/ingestion/test_heading_detection.py`
pins that limit rather than leaving it to be discovered.

**There is no chart modality, and a chart is still retrievable** (changed
2026-09-05). `chart` was a selectable modality that queried `chart_descriptions`
and returned nothing every time: the only writer was `ChartAnalyzer.index_chart`,
and nothing in `app/` ever constructed a `ChartAnalyzer`. "Inert on purpose" was
the previous reading of that, and it was too kind -- the path cost a retrieval
slot and an INFO line per query and could not have paid for itself.

**It was deleted rather than connected, and the capability did not go with it.**
A chart is an image, and `_index_images` already captions images through
`app/ingestion/extraction/vision.py`, which follows `IMAGE_CAPTION_BACKEND` and
`MODEL_BACKEND` and falls back between them -- the path `ba55bf70` fixed so a
caption survives an unreadable OCR, which is exactly the chart case. What
`ChartAnalyzer` added over that was a `chart_type` label and a best-effort `data`
dict; what it cost was a second vision path that built its own `AsyncOpenAI`
against a `VISION_MODEL` setting the admin page cannot reach, outside the egress
redaction the model wrapper applies, gated by an English keyword scan
(`"bar chart"`, `"axis"`) over a caption this system writes in Chinese as often as
not. Connecting it meant rewriting all three of those, after which the additions
are some thirty lines on the path that already runs. If structured chart data is
ever wanted, that is where it goes.

`tests/retrievers/test_every_modality_has_a_producer.py` walks the chain the
defect actually broke -- collection name → the `index_*` method that writes it →
that method's class → a construction of that class in `app/` -- because the two
obvious checks both pass on the broken code: `chart_descriptions` *was* named in
`app/`, by its producer, and `index_chart` *did* write it correctly. Run against
the previous commit it fails twice, which is how `text_chunks` turned up: the
text modality was deleted in `2f94cce6` but `retrieve` kept
`self._retrieve_text(...)` behind an `if "text" in modalities`, a call to a method
that no longer exists, and `retrieve_by_doc_id` kept the collection in its map.
Both are gone, and `retrieve_by_doc_id` itself was deleted the next day -- it had no
callers at all.

**Visual embeddings are gone** (2026-09-05), and they are the sharpest version of
the defect above because every static check passed. `_retrieve_images` queried a
`visual_embeddings` collection on **every** image search; the collection is written
by a branch of `index_image`, `if image.visual_embedding:`; and `visual_embedding`
was set only by `ImageProcessor.process_images_batch`, which had no caller. So the
class was constructed, the writing *method* was called, the collection name
resolved to a real writer -- and the branch never once fired, so the read raised
per query into an INFO log. `test_every_modality_has_a_producer` walks that chain
and still passes on the broken code; the dead link is a branch condition, and it
says so rather than implying it caught this. It was found by reading.

Deleted with it: `app/ingestion/embedding/` (the `VisualEmbeddingProvider`
boundary and its ColPali seam), `VISUAL_EMBEDDING_ENABLED`,
`VISUAL_EMBEDDING_BACKEND`, and four `ImageContent` fields whose only writer was
`process_images_batch`. ColPali-style visual retrieval is a real idea and this was
not an implementation of it -- nothing ever produced a vector. Rebuilding it on the
model configuration added in `062ca7d2` is a project, not a reconnection.

**These collections sit outside the corpus `similarity_search` guards**, so both
of that function's checks are reproduced here deliberately. `_scope_filter`
constrains by tenant *and* by source or document *and* by `_owner_clause` -- the
same helper the store uses, not a second implementation -- and `index_image` /
`index_table` write `owner_user_id` and `visibility` alongside the tenant. An
absent key does not match `$eq`, so anything indexed without those fields is
invisible rather than public, which is why `visibility` defaults to private
rather than to `""`. `tests/security/test_multimodal_indexing.py` pins the
refusals.

**Everything on this path is synchronous, and that shaped it.** `ingest_paths` is
reached from `asyncio.to_thread`; `index_image` and `index_table` were `async`
while awaiting nothing, and dropping the keyword is what let ingestion call them
at all rather than driving an event loop from a worker thread.

**PyMuPDF is the optional `multimodal` extra and must stay a lazy import.** Three
modules imported it at module scope, which was survivable only while nothing
imported them -- ingestion does now, so on an installation without the extra the
first document containing an image or a table would have crashed the ingest. All
four modules import without it, which is what `app/services/multimodal/__init__.py`
has always claimed.

### Retrieval Strategy

**Hybrid Retrieval** ([app/retrievers/hybrid/retriever.py](app/retrievers/hybrid/retriever.py)):
- **Vector search**: ChromaDB, embedded by one of exactly three things --
  `LocalHashEmbeddings` (the `local` backend's default: deterministic blake2b
  hash buckets, **not semantic**, which is why the admin console reports it
  `degraded`), OpenAI, or Ollama. **There is no sentence-transformers embedding
  model**, and this line claimed "Sentence-Transformers BGE-M3 embeddings" until
  2026-09-09; `sentence_transformers` is imported only for `CrossEncoder`, by the
  reranker and the NLI stage. Anyone reading the old claim would have taken a
  correctly-reported degraded embedding for a misconfiguration.
- **BM25 search**: Jieba tokenization → Rank-BM25
- **Fusion**: Reciprocal Rank Fusion (RRF), over one ranked list per **(source, query)**
  pair -- not per source (2026-09-04). An adapter runs each of `plan.queries` and returns
  `RankedGroups`, one ranked tuple per query in that order; `_retrieve_source` masks each
  group separately, so dropping an unauthorized item closes the gap inside its own list
  rather than merging lists.

  This landed in two steps, and the first is worth remembering because it was not enough.
  A source used to fold its queries into one list, and RRF scores by *position*, so the
  second query's best hit arrived at rank `top_k + 1` and was charged a rank it had not
  earned. That was never dormant, though it was uneven: `QUERY_REWRITE_ENABLED` defaults
  true and the rule rewriter needs no LLM, and measured, a Chinese question containing
  punctuation yields 2-3 queries and a multi-word English one yields 3 -- but a short
  punctuation-free Chinese question yields 1, where the fold cost nothing. Interleaving
  (step one) moved that hit to rank 2 rather than rank 1: smaller, still wrong, and still
  growing with the number of queries. Keeping the lists apart (step two) removes it --
  every query's rank-1 gets the same `1/(k+1)`, and a document two queries both rank first
  accumulates two full contributions instead of one full and one discounted.

  `flatten_ranked_groups` survives as the flat *view* -- result counts, diagnostics, and
  the graph adapter's prior evidence -- and still interleaves, but nothing about ranking
  depends on it any more.

  **Not visible in `make eval-retrieval`**, which runs one query per source
  (`rewrite=False`), so there is a single group and fusion is unchanged: MRR stays 0.9688
  across step two. That is why the property is pinned by unit tests over
  `reciprocal_rank_fuse` rather than by the corpus metric -- a number that cannot move is
  not evidence.
- **Planner sub-queries reach the retrievers** (wired 2026-09-04). `PlannedTask.prompt` had
  exactly one reader in all of `app/` (`rag_pipeline.py`, for a diagnostics dict), because
  `_source_plan` hardcoded `queries=(query,)` and `RAGAgentService.retrieve` opened with
  `del plan`. A decomposed question therefore ran one search on the original wording --
  while the API returned the sub-queries to the client as `decomposed_query`, reporting
  work that never happened. `_source_plan` now builds `(question, *sub_queries)`.

  Four things about that shape are load-bearing. **The original question stays at index
  0**, because `KnowledgeOrchestrator` reads `sources[0].queries[0]` twice -- as
  `primary_query`, the single string reranking scores every candidate against, and as the
  rewriter's input -- so a sub-query there would rerank the whole result set against one
  facet. **De-duplication uses one shared definition** (`app/knowledge/queries.py`,
  imported by both the agent and the orchestrator; the agent must not import the
  orchestrator): a direct plan's single task prompt *is* the question, and
  `reciprocal_rank_fuse` accumulates per appearance, so a duplicate silently double-weights
  everything it returns. **`web` and `memory` are excluded** -- `_retrieve_web` calls
  `run_web_research` per query and concurrent `DDGS()` construction has wedged this process
  at zero CPU before, so an N-fold multiplier on third-party search is the worst failure
  mode available here. **The cap is enforced twice** from one constant
  (`MAX_PLAN_QUERIES_PER_SOURCE`), in `_source_plan` and in `_bounded`, because `_bounded`
  only runs on the decider path and `capabilities.py` constructs the agent with no decider
  -- a cap there alone would guard a path that does not exist in production.

  `_comparison_plan` now emits the bare target rather than "Retrieve authoritative evidence
  about X": those prompts are search queries now, and `bm25_search` matches on shared term
  membership, so the English boilerplate would have made every chunk containing "evidence"
  a candidate for a comparison usually asked in Chinese. Note that `_comparison_plan` runs
  *before* the `enable_decomposition` check in `PlannerAgentService.plan`, so
  comparison-shaped questions get multi-query retrieval by default.
- **Graph retrieval**: runs for both the `graph` and `hybrid` routes (fixed 2026-08-29; `graph` previously degraded silently to vector+BM25)
- **Two-phase retrieval** (added 2026-08-31): `KnowledgeOrchestrator` runs sources in one
  `asyncio.gather` because they are independent. An adapter that implements
  `PriorEvidenceAdapter` declares it is not, and gets a second phase fed the first phase's
  evidence. `GraphKnowledgeAdapter` is the only one, and it asks for that phase **only when
  `GRAPH_RAG_ENHANCED` is on** — with the switch off there is no reader for the prior
  evidence, so the deferral would buy nothing and cost the overlap.

  The cost is real: a deferred source's duration lands on the critical path instead of
  hiding under the others. Phase two therefore inherits what is *left* of
  `STAGE_TIMEOUT_RETRIEVAL_MS` rather than a fresh copy of its plan timeout — otherwise two
  phases could take `phase_one + phase_two` and trip the stage ceiling, turning a sharper
  graph lookup into a degraded stage, which is strictly worse than the plain lookup it
  replaced.

  **Prior evidence tunes retrieval; it must never widen it.** What crosses into
  `run_graph_rag` is a quality *score* over the retrieved text plus page/format metadata.
  `run_graph_rag_with_pdf_context` does not read entities out of the documents to query
  with, and `allowed_sources`/`owner` remain the ones `privacy_permission` resolved. So a
  document that argues for its own importance can buy itself a larger `max_neighbors` and
  nothing else. Do not extend this to letting document text choose which entities to look
  up: that is retrieved content steering retrieval, and the author of a retrieved document
  is not always the person asking — the same reasoning that keeps tool selection blind to
  evidence.

  Phase outcomes are reassembled **by index, not by source name**: `KnowledgeStrategy.sources`
  carries no uniqueness constraint, and downstream `zip(source_plans, outcomes, strict=True)`
  reads `plan.required` off the pair, so keying on the source would misattribute a failure.
  A failed source contributes no prior evidence — a timed-out source has no results, not zero
  results, and feeding its silence to the quality estimator reads as a poor corpus.

  `app/agents/rag/cache.py` was rewritten in the same pass. It memoizes pure functions over
  in-memory text, but wrapped an *async* cache by calling `asyncio.get_event_loop()` and
  `run_until_complete`. `run_graph_rag` reaches it from `asyncio.to_thread`, where
  `get_event_loop()` raises and the fallback installs a private, never-closed loop per pool
  worker — and an `asyncio.Lock` driven from several loops serializes nothing. The mirror
  failure waited on the main thread, where `run_until_complete` on a *running* loop raises.
  Neither ever fired because nothing reached the code. It is a plain synchronous TTL+LRU now;
  do not reconnect it to `app/services/caching/`, which exists for values worth a network
  round trip and is what made an in-memory memo look like it needed a loop.

  `app/agents/shared/cache.py`, the router decision memo, had the identical defect and took
  the identical fix, so the rule generalises: **nothing reached from `asyncio.to_thread` may
  drive an event loop.** `get_event_loop()` raises in a worker thread, and the fallback of
  installing a private one leaves a loop open per worker for the life of the process. A memo
  over in-memory values is a dictionary lookup; it never needed a loop.
  `tests/agents/test_router_cache.py` pins that.
- **Reranking**: BGE-Reranker-V2-M3 (top 5 results)
- **Retrieval width** (wired to the chat path 2026-08-31): how wide a search is now depends
  on the question and on the plan, and both decisions live in `KnowledgeAgentService` —
  the Agent shapes a search, the orchestrator executes it.

  `app/knowledge/width.py` holds the one complexity definition (long query / comparison
  wording / multiple question marks, 0-3) and two call sites scale different bases from it:
  the Knowledge Agent grows `TOP_K` (4) and `RERANKER_TOP_N` (5), the legacy hybrid path
  grows `VECTOR_TOP_K`/`BM25_TOP_K` (6). Keeping the bases apart matters — borrowing the
  hybrid default would have widened every *simple* query too, which is a different decision
  from making complex ones wider. It moved out of `app/retrievers/hybrid/adaptive_params.py`
  because the Knowledge Agent must not import a retriever; `app/retrievers/hybrid/`
  re-exports `adaptive_retrieval_params` under its old name.

  Reranking widens with the search: `KnowledgeStrategy.rerank_top_n` (None means use the
  setting) exists because feeding the reranker more candidates while holding its output
  size fixed just discards the extra ones. Before this, `DYNAMIC_RETRIEVAL_ENABLED` and the
  `DYNAMIC_*_CAP` settings only reached `candidate_collection.py`, which the chat path does
  not use, so every source got a flat `TOP_K` however complex the question was.

  **`TaskBudget.max_retrievals` bounds the source *count*, not the width.** The planner
  derives it as 2 (the required local pair) + 1 for a hybrid route + 1 for web — a count of
  retrieval calls, which is exactly the source list `_rule_strategy` builds. It used to be
  summed, checked against `PLANNER_MAX_RETRIEVAL_BUDGET`, and dropped. The ceiling is now
  spent in the planner's own order (required pair → sources the *route* hinted → keyword
  matches): truncating in discovery order spent the web slot on `multimodal`, because the
  keyword rules append `web` last. A plan totalling zero is a plan with no retrieval task
  (a pure tool call), which is the absence of an instruction rather than an instruction to
  search less, so the service ceiling stands.

### Configuration System

**Essential config files** in `config/`:
- `router_calibration.json`: Few-shot examples, confidence thresholds. Only read when `ENABLE_CALIBRATION=true` (off by default); with calibration disabled, routing relies solely on the LLM classifier's own confidence output.

**Runtime config**: [app/core/config.py](app/core/config.py) intentionally does **not** read a root
`.env` file — it reads `.runtime/{APP_ENV}.env`, generated by
`deploy/scripts/config.py render` from `config/env/` + `config/profiles/` (or a file pointed to by
`RUNTIME_ENV_FILE`). Setting values in a root `.env` has no effect; export real environment
variables or run the render step first.

`.runtime/` starts empty. Until `make config-render ENV=development` is run,
`Settings` falls back to its hardcoded defaults for every field — including
`MODEL_BACKEND=local`. Run the render step (or export real environment variables)
before treating any configured value as active.

**`MODEL_BACKEND=local` means there is no LLM in the loop at all**, and it is what a fresh
checkout runs — so it is the state most first impressions are formed in. `local` resolves to
`LocalEvidenceChatModel` (`app/services/models/runtime.py`), an offline stand-in that keeps
the app usable with no API key and no Ollama: it routes by keyword (`_route_json` —
关系/依赖/graph/relation/路径 → `hybrid`, everything else → `vector`) and assembles an answer
out of the evidence sections of its own prompt. Every quality number in this file — router
accuracy, citation completeness, P@5 — describes the LLM path and means nothing on this one.
`MODEL_BACKEND=local` in the real process environment additionally **overrides persisted
admin model settings** (`_local_backend_forced`), so a deployment that sets it cannot be
talked out of it from the admin UI -- and since 2026-09-04 the UI says so. `GET/POST
/admin/model-settings` return `environment_pinned` and a reason, and the page leads with a
warning banner. Without it an admin could save an OpenAI key and model, get a success
response, see the values echoed back and an audit row behind them, while every answer still
came from `LocalEvidenceChatModel` -- the same "reports something other than what runs"
failure as the old `advanced-rag/config` endpoint.

The write is **accepted**, not refused, which is the one place this differs from
`POST /admin/config/values` next door. That endpoint refuses a write to an
environment-pinned value because the write would go to a layer the process does not read;
this one persists correctly and takes effect the moment the pin is removed, so refusing it
would block legitimate preparation.

The same pass fixed a description that promised the opposite of the code, and the
correction has since been overtaken -- both halves are worth keeping, because the field has
now been wrong in two opposite directions. The `enabled` flag was first documented as
applying the global config "to users without personal overrides", while `get_chat_model`
resolved `global_override or user_override`: an enabled global config won over *every*
user's own settings, so an admin ticking that box on the old promise would have moved
everyone's traffic silently. The replacement wording said it overrode "their personal API
settings" -- true then, and false from 2026-09-08, when per-user model configuration was
removed. It now says what the switch chooses between: the administrator's configuration and
the deployment's own environment. `test_the_enabled_flag_describes_what_it_actually_does`
asserts the absence of both wrong forms, not just the first.

Having no model to hide behind is why this is the path where prompt scaffolding leaks into
prose. It has narrated itself, echoed `ContextBuilder`'s `[E1] document=…; layer=…` header
as though it were text, and returned its own answer template as the answer.
`tests/services/test_answer_readability.py` pins all of it: the reader must never see the
machinery that produced the answer.

**A value read with `os.getenv` cannot be configured.** pydantic-settings loads
`.runtime/{APP_ENV}.env` into `Settings` **without exporting anything into the process
environment** — with `APP_ENV=development` in that file, `Settings().app_env` is
`development` while `os.getenv("APP_ENV")` is still unset. So `make config-render` cannot
set such a key, nor can anything that pushes values into `Settings`; it has to be a real
exported environment variable, present before the module is imported. None of the keys
below appeared anywhere in `config/env/`.

An AST census on 2026-09-01 found **47 live keys** outside `Settings`: 2 in the router,
2 in the request middleware (one of them `STRICT_CSP`, which picks the Content-Security-Policy),
5 in an admin endpoint, 2 duplicated in the Self-RAG evaluator, 37 behind the helper
functions in `app/agents/shared/config.py`, plus 5 in a module with no importers at all.
**All of them are gone**, and `app/` now contains no environment read outside the allowlist
below. See `docs/superpowers/plans/2026-09-01-configuration-management.md`.

The 37 did not all deserve migrating, which is the more useful half of that pass: **20 had
no reader anywhere** and were deleted rather than carried into `Settings` — including
`CASCADE_USE_FOR_VALIDATION`, whose branch logged "is retired" and then did the same thing
either way. Thirteen became fields. The four `ANSWER_WEIGHT_*` scoring weights stayed in
`app/agents/shared/config.py` as plain literals: they are one scheme that has to sum to 1.0,
and four independently settable knobs that must agree is a footgun, not a feature. Migrating
a constant nothing reads would have made the configuration surface bigger and no more
configurable.

**Precedence is declared once**, by the source order in
`Settings.settings_customise_sources`:

```
init > real process environment > configuration centre > .runtime/{APP_ENV}.env > defaults
```

`RemoteSettingsSource` (`app/core/remote_config.py`) is the configuration-centre slot; the
Nacos adapter behind it (`app/core/remote_config_nacos.py`) imports the SDK lazily, so an
`ImportError` degrades to the snapshot and an installation that has not adopted a
configuration centre never needs the dependency (`pip install -e .[config-centre]`). The
source returns `{}` unless `NACOS_ENABLED` is true, which is the default.

**The bootstrap must be a real environment variable, never a key in `.runtime/*.env`** —
that file is read into `Settings` without being exported, so a bootstrap key placed there is
silently ignored, which is the same trap the rest of this section is about. It belongs in the
process environment, which for a deployment means `environment:` in
`deploy/compose/compose.config-centre.yaml`:

| key | default | |
|---|---|---|
| `NACOS_ENABLED` | `false` | nothing below is read while this is off |
| `NACOS_SERVER_ADDR` | — | required when enabled |
| `NACOS_NAMESPACE` | `""` | the public namespace |
| `NACOS_GROUP` | `DEFAULT_GROUP` | |
| `NACOS_DATA_IDS` | `querymind` | comma-separated; **later ids override earlier ones**, the same rule the render step uses for its layers |
| `NACOS_USERNAME` / `NACOS_PASSWORD` | `""` | never `Settings` fields — see the allowlist below |
| `NACOS_TIMEOUT_MS` | `3000` | per fetch |
| `NACOS_POLL_INTERVAL_MS` | `30000` | how long a console edit takes to reach a running process |

`scripts/create_admin.py` creates the local development administrator, because until
2026-09-01 there was no account with the `admin` role at all and the admin surface could not
be opened by anyone. It is a fixture: the password comes from `ADMIN_PASSWORD` or is
generated and printed once, and is never written to a file in the repository.

`scripts/verify_config_centre.py` drives the **real** SDK against a stub server with no
container, and is the thing to run after touching the adapter or bumping the pin: a fake
client answers whatever shape it is asked for, so the unit tests cannot catch this
repository's calls drifting from the SDK's.

**`GET /admin/model-settings/effective` answers a different question from every other
admin surface** (added 2026-09-04): not "what did I save" but "what will the next question
use". They come apart quietly. The reranker and the NLI cross-encoder are both loaded with
`local_files_only=True`, so a model that was never downloaded returns `None` rather than
raising -- retrieval falls back to `lexical_rerank`, validation falls back to a
deterministic scorer, both keep answering, and from outside a degraded stage is
indistinguishable from a healthy one. `MODEL_BACKEND=local` discards a saved provider
config outright, and on the offline backend there is no language model at all.

So each component reports a **status**, and `degraded` is the one worth having: configured,
running, and not doing what its name implies. Six are reported, in the order a question
moves through the system: `ocr`, `image_caption`, `embedding`, `reranker`, `chat`,
`validation_nli`.

The two image components read together on purpose. OCR is the half that fails on a fresh
machine -- pytesseract missing, or the binary not on PATH -- and captioning is what keeps an
image searchable when OCR reads nothing, so an operator seeing `ocr: unavailable` needs to
know whether the other half is on. Captioning reports **configuration readiness, not
liveness**: it makes no network call, because probing a vision endpoint is unbounded and an
admin page that can hang on a misconfigured base URL is worse than one that reports what it
can check. It does report the backend *order*, since `auto` follows `MODEL_BACKEND` and
falls back, which no single setting shows. Probing loads the optional models, which is
why this is an admin endpoint and not part of a health check -- the cost is the one the
first real query would have paid, once per process.

`IMAGE_CAPTION_ENABLED`, `IMAGE_CAPTION_BACKEND`, `OPENAI_VISION_MODEL` and
`OLLAMA_VISION_MODEL` are editable too, under a new `images` group -- the page renders
whatever groups it is sent. Captioning was worth exposing only after its output stopped
being discarded on the images that need it (see Multimodal retrieval); a switch that
turns on something inert is the defect this file keeps recording, not a feature.

`ENABLE_RERANKER`, `RERANKER_MODEL_NAME`, the four `CASCADE_ENABLE_*` switches, both
cascade timeouts, `NLI_MODEL_NAME` and `NLI_MAX_SENTENCES` became editable in the same
pass. Each needed its cache cleared by `apply_config_reload` first: `clear_model_caches`
covers the chat and embedding models only, so the reranker's own `lru_cache` kept the old
model while the page reported the new name. `test_the_reload_reaches_every_cache_that_holds_an_editable_setting`
now enforces that -- it finds every `@lru_cache` function reading an editable field and
requires the reload to clear it, following one level of indirection through the named
clearers, and it was verified able to fail by removing the reranker's.

**That guard sees `@lru_cache` and nothing else, and a hand-rolled cache slipped past it**
(fixed 2026-09-06). `decide_route` is memoized in `app/agents/shared/cache.py` by a TTL/LRU
store of this repository's own, on a key of question and hints only -- and its result reads
two editable settings, `ENABLE_CALIBRATION` through `_calibrated` and
`ENABLE_WEB_ROUTE_DOWNGRADE` through `_llm_route`. So toggling either from the console
reported success and left every question already in the cache routing the old way for up to
thirty minutes. `clear_router_decision_cache` existed, did exactly this, and had no caller
outside tests; it is in the reload sequence now, pinned by
`test_the_reload_empties_the_router_decision_memo`. Adding a cache that is not an
`lru_cache` means adding it to the sequence by hand -- the guard cannot find it for you.

**What an administrator may change is an allowlist**, `app/core/config_schema.py`, not an
annotation per field. `Settings` has 235 of them; annotating individually would scatter a
security-relevant decision across 236 lines and leave "what can console access reach?"
with no single answer. It is opt-in — a new field is not editable until it is named — and
`tests/core/test_config_schema.py` asserts by *shape* that nothing matching KEY, SECRET,
PASSWORD, TOKEN, PATH, URL, DSN, CORS or ORIGIN ever appears there, so a future addition has
to defeat the rule deliberately rather than by inattention.

`GET /admin/config/schema` returns each editable field with its current value and **which
layer supplied it**, and `POST /admin/config/values` writes to the configuration centre and
reloads. Two things it refuses, and both prevent the console from claiming a change it did
not make: a write with no configuration centre configured (there would be nowhere to put it
that the process reads), and a write to a value pinned in the process environment — the
environment outranks the centre, so it would succeed and change nothing. The browser
disables those inputs too, but that is a convenience: the rule is enforced server-side
because the browser is not where it can be.

**Each edited key is written back to the document that already defines it**, and each such
document is rewritten whole rather than patched. Writing everything to one document instead
put the same key in two places with the later id silently winning, so the page showed a value
from one document while the edit landed in another — found by clicking Save against a real
server. A key no document defines yet goes to the last data id, which is the fallback
precisely because later ids override earlier ones. The centre owns version history and
rollback; merging in this layer would be a second, worse implementation of both.

Verified end to end against a real Nacos 2.4.3, which is also where two defects the unit
tests could not see turned up: `RemoteDocuments` had no `publish` method at all — it had
landed on the wrong class in a refactor, and all eleven endpoint tests passed because the
fake they inject implements whatever it is asked for. One test now fakes only the client, the
actual network boundary, and drives the real store. Deployment note: with
`NACOS_AUTH_ENABLE=true` and the embedded store, the user table starts empty and
`nacos/nacos` fails with "User nacos not found" until `POST /nacos/v1/auth/users/admin`
bootstraps the account.

**The process environment sits above the centre on purpose**: a deployment needs one way to
pin a value the console cannot move, which is what `MODEL_BACKEND=local` already does to
persisted admin model settings. The rejected alternative — fetching remote values at startup
and writing them into `os.environ` — destroys exactly that, and smuggles values past
`Settings`'s validation.

**Nothing may break startup.** `get_settings()` is on the path to everything, so the source
degrades in three steps: the remote document, the snapshot written by the last *successful*
fetch (`.runtime/remote-config/`), then nothing at all — which simply leaves the lower
sources in charge. The SDK is called with `no_snapshot=True` because this layer keeps its
own: letting the SDK substitute its cache would make "the server answered" and "it did not"
indistinguishable, and that log line is what an operator has when a value fails to take
effect.

**A settings source must return values keyed by field *alias*.** `{"ENABLE_CALIBRATION":
True}` applies; `{"enable_calibration": True}` is **silently ignored** — `Settings` validates
by alias and `extra="ignore"` drops the rest, with no error anywhere. Aliases are what
`config/env/*` and the rendered file already use, so one name follows a value from the
repository to the console.

**Change detection is polled, not pushed, and that is not a preference.**
`nacos-sdk-python` 1.x does it in `_init_pulling`, which builds a
`multiprocessing.Manager()`, a `multiprocessing.Queue` and a ten-thread callback pool — and on
Windows, where the start method is spawn, registering a watcher never returned (verified twice
against a stub server, with and without a `__main__` guard). `watch_remote_config` runs one
daemon thread that re-fetches every `NACOS_POLL_INTERVAL_MS` (default 30s) and compares a
digest of the documents. The cost is up to that much latency on a console edit; what it buys
is one less process, one less thread pool, and the same behaviour on every platform.

**The SDK dependency is pinned to `>=1.0.0,<2.0` as a design constraint.** 2.x and 3.x import
as `v2.nacos`, not `nacos`, and their `get_config` is a coroutine — and this client is called
from synchronous `Settings()` construction, reachable from a request handler via
`reload_settings()`. Driving it there means `asyncio.run` (which raises inside a running loop)
or a private loop per call, the exact defect already fixed twice in this repository.

**There is one way configuration changes at runtime**, `write_config_values()`, and both the
admin page and the replay autotuner go through it. The autotuner used to assign its patch
onto the live `Settings` object instead — which failed twice over: the change belonged to no
layer, so it was lost at the next reload, and the page's "which layer did this come from"
column had no way to know. It now recommends, and applying inherits every refusal, including
the one for a value the process environment pins.

`requires_restart` is `False` on every editable field, and that is an audited claim rather
than a default -- and since 2026-09-04 an enforced one:
`tests/core/test_editable_settings_are_reloadable.py` fails if an editable field is read
through a `settings = get_settings()` bound at *module scope*. Six modules do that
(`app/api/dependencies.py`, `deps/{admin,documents,sessions}.py`,
`utils/{auth_helpers,memory_helpers}.py`); `get_settings` is `lru_cache`d and a reload
calls `cache_clear()`, which builds a new object, so those six keep the one they captured
at import for the life of the process. No editable field is read through them today, which
is why the test asserts rather than ratchets -- but it held by coincidence rather than by
construction, and the failure it prevents is silent: the console would report success and
the process would keep the old value. Same hazard as the `CASCADE_*` module global next
door, reached from a different direction. Verified able to fail by adding `MODEL_BACKEND`
(read in `deps/admin.py`) to the allowlist. The audit itself: each consumer either reads `get_settings()` per use, or is held by an object
`RAGPipeline` builds per request, or is rebuilt by the reload. The retrieval cache was the
one exception — it bakes its TTL in at construction and lives in a module global — so the
reload clears it rather than the page carrying a caveat.

A change pushed from the console and the admin endpoint's reload run the **same** sequence,
`app/api/application/config_reload.py::apply_config_reload()`. A watcher that cleared its own
subset of caches would be a second, quieter definition of "reloaded", and the difference
would only ever surface as "it took effect when I clicked the button but not when I saved it
in the console". That function's limit is worth knowing: a value already read into a
module-level constant is not revisited, so the legacy constant block keeps its start-up
values until the process restarts.

**A key in a configuration layer that `Settings` does not know is dead**, and dead in the
quietest way: validation is by alias with `extra="ignore"`, so an unrecognised key in
`config/env/*` or `config/profiles/*` is dropped without an error, and the render step copies
it into `.runtime/{APP_ENV}.env` where it looks exactly like a live setting. Two were found
that way on 2026-09-01 — `QUERY_RESULT_CACHE_BACKEND`, a sibling of the real
`RETRIEVAL_CACHE_BACKEND` that was never implemented, and `DEBUG`, which had no reader at all
while `deploy/scripts/config.py` enforced "DEBUG must not be true in production", a safety
rule about a value that could not have an effect. Both are gone, and
`tests/core/test_config_layers_are_live.py` checks every committed layer key against the
aliases, with a small allowlist for keys the deployment itself consumes.

`tests/core/test_config_has_one_source.py` keeps it that way: an AST guard that every
direct environment read in `app/` is in an allowlist keyed on `path::enclosing_function`
**with a reason**. It carried a ratchet over the legacy constant block as well until that
block was emptied; a guard that guards nothing is one more thing to read and no protection,
so it went with it. These reads are legitimately exempt and stay:
`resolve_runtime_env_file` (it chooses the settings file, so it cannot live in it),
`remote_config._bootstrap` (the same chicken-and-egg one layer out: it configures the source
that supplies `Settings`, which is also why `NACOS_PASSWORD` never becomes a field),
`_local_backend_forced` (a deployment pinning the local backend must beat persisted admin
settings), conda-environment diagnostics, and pytest detection.

Two consequences worth knowing. `ENABLE_WEB_ROUTE_DOWNGRADE` silently rewrites a `web`
route to `vector` inside `decide_route` — a third and invisible answer to "who authorized
the web", see Knowledge Agent above. And **anything read at import time cannot be
reconfigured at runtime**: the router's calibrator and the request-metrics deque were both
bound at import and are now resolved on first use, because a value that is only read once,
before `Settings` is loaded, is not configuration.

**`GET /api/advanced-rag/config` reports the switches that actually gate its two
features** (fixed 2026-09-01). Every value it returned was unrelated to what ran:
`query_decomposition.enabled_by_default` came from `ENABLE_QUERY_DECOMPOSITION` while the
real switch is `QUERY_DECOMPOSE_ENABLED`, **which defaults to on** — so the page reported
`false` on a feature that was running; `self_rag.enabled_by_default` came from
`ENABLE_SELF_RAG` while the gate is `VectorRAGConfig.enable_evaluation`; and
`max_sub_queries` came from an environment variable rather than the bound `QueryDecomposer`
enforces (now the named `DEFAULT_MAX_SUB_QUERIES`). A configuration page that reports
something other than the running configuration is worse than no page — it is the reason
this section exists.

**Additional config**: [app/agents/shared/config.py](app/agents/shared/config.py) holds the
`VectorRAGConfig` that `app/agents/rag/vector.py` reads, plus the four `ANSWER_WEIGHT_*`
literals described above. Five sibling sections — router, graph_rag, react, synthesis,
quality — and the seven accessors that were their only readers were deleted on 2026-09-06;
their defaults had drifted into stating the opposite of what runs, so the file was actively
misleading as a description of the configuration. Do not read a default here as evidence
that a feature is on: check the `Settings` field.

### Model configuration is an administrator's, and applies to everyone

Ordinary users do not configure models. An administrator sets one configuration at
`/admin/model-settings` and it is what answers every user's questions; with it disabled,
the deployment's own environment answers. That is the rule, stated 2026-09-08, and it was
already how answers were produced -- but only by accident, and the surface said otherwise
in the most expensive way available.

**Three endpoints collected a credential nobody would ever use.** `GET`/`POST
/user/api-settings` and `/user/api-settings/test` were gated on `_require_user` alone, the
`ApiSettings` drawer was rendered on the chat page for every signed-in account, and the
posted API key was encrypted into that user's row. A user could pick a provider, paste
their own key, press Test, and get **"API connectivity test succeeded"** -- because the
probe built a model from the posted values directly, so the credentials really did work.
Then every question they asked went to the administrator's model.

**Nothing on the answer path had ever read any of it.** `_request_chat_override()` read a
ContextVar that only `probe_chat_model_configuration` ever set with content;
`OrchestrationEngine` merely re-read and re-published whatever was already there, which on
a real request is `None`. So `get_chat_model`'s `global_override or user_override` had a
second operand that was always `{}` -- a fallback that existed in the reading and not in
the running. That is why nobody noticed the feature did nothing: **the only surface that
could have contradicted it was the Test button, and the Test button worked.**

What was removed: the three endpoints, `UserApiSettings`/`View`/`Response`, the five
`config_store` functions behind them, `AuditAction.USER_API_SETTINGS_TEST`,
`_api_settings_view`, the `api_settings` parameter on `request_context`, and the
`ApiSettings` island in the frontend (four components and two helper modules).

**The seam went with the feature, deliberately.** `request_context` could have kept its
parameter harmlessly -- it was harmless for the feature's whole life. But a parameter named
for a per-user model is an invitation to wire one back in a call site at a time, and
`test_the_request_context_cannot_carry_a_model_configuration` asserts the signature is
exactly `timeout_ms` and `overload_mode`.

**Deleting the endpoints does not reach the stored keys**, so
`purge_user_api_settings()` runs from the lifespan and clears the retired key from every
user row. An encrypted third-party credential that nothing reads is the only kind whose
disclosure costs its owner everything and buys them nothing. It is idempotent, skipped
under pytest for the reason the administrator bootstrap is, and clears **one key** rather
than resetting a row -- `preferences` beside it survives, which is asserted.

**`GET /user/active-model` replaced them, and reports rather than accepts.** It exists
because the change would otherwise have deleted something real: `useSettingsPolling` used
the old endpoint only to read the *global* state and toast when an administrator changed
the model, which is worth more now that a reader cannot change it back. It consults
`_local_backend_forced()` as well as the saved configuration, because with
`MODEL_BACKEND=local` pinned `get_chat_model` discards the override outright -- reporting
it as active would be this file's recurring failure, a page saying something other than
what runs.

**One defect was found by fixing this rather than being the reason for it.** The probe
published its payload into the ContextVar and let `get_chat_model` pick it up -- and
`get_chat_model` consults the *saved* global configuration **first**. So an administrator
pressing Test on a new provider while a configuration was already enabled probed the old
one and was shown its success as the new one's. `probe_chat_model_configuration` builds
the model from its argument now, through `_chat_model_from_override`, which also collapses
the three duplicated copies of "assemble an overridden chat model" into one.

`tests/security/test_model_configuration_is_admin_only.py` (9) is mostly negative, because
what has to hold is that the surface does not come back: no `api-settings` path under any
method, `/user/active-model` accepting only `get`, no `AdminModelSettings` body outside
`/admin/`, no `user_override` in `runtime.py`. Each of the nine was verified able to fail
by restoring the shipped behaviour it pins -- seven mutations, seven distinct rednesses.
`SettingsDrawer.test.tsx` (7) pins the other half: the drawer offers no textbox, combobox,
slider or spinbutton, and its only button is the close control.

**The drawer survived because it was never only about models.** It hosts `IntegrationsPanel`
and `MemoryPanel`, so `ApiSettings.tsx` became `SettingsDrawer.tsx` -- the model form gone,
a read-only line naming the administrator's model in its place. Measured in a browser
through the same throwaway harness the memory panel used (real components, real cascade,
only `window.fetch` replaced, deleted in the same change): **35 nodes, zero non-exempt
failures.** The three added nodes are 5.32 (`Model` heading), 14.42 (the mono
`provider / model` line) and 5.28 (the note) -- that last being exactly the
`--text-muted` on `--surface-muted` pair already recorded for the memory panel. The one
failure at 2.08 is the disabled connector's `Test` button, the inactive-component exemption
this file already records; the two skipped nodes are both on `--brand-mark-gradient`, the
logotype exemption. `__probe()` caught all three planted bad nodes first, so the scanner
was known able to fail before its pass was believed.

#### Configuring a real relay for the first time found six defects

On 2026-09-09 an Anthropic-compatible relay was configured through the admin
console -- the first time anybody had done it. Everything about the change above
was already tested and green. Six things broke anyway, and the shape they share
is worth more than any one of them: **each sat on a path that no test and no
reader had ever walked end to end.**

- **The relay branch had never run.** `AnthropicRelayChatModel` exists for
  exactly one situation, a gateway reached at a `base_url`, and the only code
  constructing it passed `streaming=True`, which its `__init__` does not accept.
  Every relay configuration raised `TypeError` at construction. The flag was
  never needed either: the adapter streams by *having a `stream()` method*.
  The same call also dropped `request_timeout_seconds`, so the relay kept a 30s
  default and `LLM_REQUEST_TIMEOUT_SECONDS` did not reach the one provider most
  likely to sit behind a slow hop.
  `tests/services/test_anthropic_relay_construction.py` pins both, and
  parametrizes over the constructor's parameters so a *second* unsupported
  keyword fails the same way rather than waiting for the next person to configure
  a relay.

- **The client gave up before the server did.** `services/http/client.ts`
  defaults to a 30s abort; `STAGE_TIMEOUT_TOTAL_MS` is **120s** and synthesis
  alone may take 30s. Measured on the first real question: **52,943ms**, well
  formed, with citations -- and the browser had already aborted it at 30s and
  rendered "Request timed out" with no sources, while the server logged `200 OK`.
  A client timeout shorter than one of the server's stages throws away the whole
  degradation design, which exists precisely to turn a slow run into a marked
  answer rather than nothing.

  The fix declares the deadline to **both** ends: `timeout_ms` (a field wired in
  2026-08-31 that the frontend had never once sent) narrows the server's budget,
  and the client's abort sits a margin *above* it, so the server always reaches
  its own deadline first and answers with its degradation path. Equal values
  would leave the race to scheduling.

- **The panel that exists to be authoritative went stale on save.** The
  `EFFECTIVE CONFIGURATION` fetch was `useEffect(..., [])` -- mount only, with a
  correct comment explaining why it must not run on every patch (probing loads
  the optional models). But a save is the one event that invalidates it, so after
  saving a provider the page showed `chat DEGRADED local -- "No provider is
  configured"` directly under a stored-configuration strip reading `Anthropic`.
  Two contradictory claims on one page, and the stale one was the panel whose
  entire job is to answer "what will the next question use". It refetches on the
  falling edge of a save and on Refresh; still never on a patch.

- **Three surfaces described the deleted per-user configuration**, and each was
  corrected in a different pass. The schema description was fixed with the
  removal itself; the **checkbox an administrator actually reads** still said
  "replaces every user's own API settings" in both locales; and both chat
  branches of the effective panel described "those with personal settings". The
  backend test passed the whole time the label lied, because the two ends had no
  place where they met. `test_the_checkbox_a_human_reads_says_the_same_thing`
  and `test_the_effective_panel_does_not_promise_a_per_user_configuration` are
  that place -- they check the locale files and the inline `defaultValue` too,
  since a missing key renders the inline copy forever and silently.

- **`test_effective_model_config.py` was reading the developer's database.**
  `_chat()` reads the stored configuration from `APP_DB_PATH`, and nothing in
  that file stubbed it -- so its environment-branch tests asserted against
  whatever was last saved in the admin console. They passed for months and went
  red the moment a provider was configured on the machine running them. The
  autouse fixture stubs it now, and the branch that had no test at all -- an
  enabled administrator configuration, the one a configured deployment takes --
  has one.

- **The model-change poller re-ran on most renders.** `useSettingsPolling` keyed
  its effect on `[onNotify, t]`; react-i18next returns a fresh `t` and the
  notifier is a new closure, so the effect tore down and re-ran constantly and
  each run repeated its seeding fetch. Measured on an **idle** page: 3 requests
  per 30s against the one a 25s interval intends, and far worse while an answer
  streams. Both are held in refs now so the effect depends on nothing; measured
  again afterwards, 1 per 30s. Same trap this file already records for the memory
  panel, reached from the other direction -- there it was an unbounded loop, here
  merely triple the traffic, which is why nobody noticed.

**What made all six visible was using the thing.** `make test`, ruff, tsc,
eslint, the design ratchet and the dead-class scan were green before and after;
none of them can ask "does a relay work", because every one of them measures the
code against itself. The relay defect in particular had been shipping since the
class was written.

One detail worth keeping for the next person configuring a provider: choose
`anthropic`, not `custom`. `custom` reports `supports_embeddings = True`, so
saving it changes the embedding signature, triggers `rebuild_all_vector_index()`,
and then sends embedding requests to a relay that almost certainly does not serve
them. `anthropic` reports False, and the page says so in its own words:
"Embedding pipeline unchanged".

#### Walking the app as a user found five more, and one open question

2026-09-09, immediately after the relay went in. Same lesson as the section
above, so it is worth stating once rather than twice: **every one of these was
found by opening a surface, and none of them is visible to any check that
measures the code against itself.**

- **Tesseract was installed and reported missing.** `_ocr()` asked
  `shutil.which("tesseract")`, and the Windows installer does not add itself to
  PATH -- so the binary sat at `C:/Program Files/Tesseract-OCR/` while the
  console said `unavailable` and image captioning stayed blocked behind it (an
  external captioning backend is fail-closed on the masking detector, which is
  this same Tesseract). `resolve_tesseract_command` in
  `app/ingestion/extraction/ocr.py` is now the single answer to "can this
  process run Tesseract", used by **both** the panel and ingestion -- a panel
  reporting `unavailable` over an OCR that works is as bad as the reverse. An
  explicit `TESSERACT_CMD` still wins and its absence is still reported, because
  falling back to a standard location when an operator named a different binary
  would silently run something they did not choose.

  Its fallback paths are written with **forward slashes**, and the comment says
  why: the first version went through a shell heredoc and shipped
  `Tesseract-OCR\tesseract.exe` with the `\t` already collapsed to a TAB. It
  resolved to nothing and read completely normally until `cat -A`. Same defect
  class as the `\\+` regex this file records for `check_sensitive.py`.

- **`_embedding()` never consulted the administrator configuration.**
  `get_embedding_model()` reads the global override before the environment;
  this reported purely from `MODEL_BACKEND`. So an admin who configured OpenAI
  got OpenAI embeddings and a panel still reading "local hash embeddings,
  degraded". Providers with no embedding endpoint still fall through, because
  for them the environment really is what runs.

- **Two `accept` lists, neither matching the server.** `ChatComposer` offered
  `.pdf` and seven image types, `DocumentsPanel` added `.md` and `.txt`, and the
  upload endpoint takes both plus `.gif` and four Office formats. So a `.md` was
  greyed out in the composer's picker while the hint beneath it read "Supports
  PDF / images / text", and no picker anywhere offered a `.docx` the server
  would have accepted. One list now (`lib/uploadFormats.ts`), compared against
  the endpoint's set by `tests/api/test_upload_formats_agree.py`. A narrower
  `accept` was never a safety measure -- `store_uploaded_files` validates the
  suffix regardless -- only a promise to whoever is choosing a file.

- **Every shared-corpus document offered three buttons that always answered
  404.** Visible and manageable are different sets and the gap is not derivable
  by a client: `list_visible_document_rows` includes `docs_path`, which everyone
  can search, while `_is_source_manageable_for_user` requires `uploads_path` --
  for administrators too, deliberately, so a `?source=` cannot reach another
  tenant's file. The panel guessed with four clauses, one of which read
  `!doc.owner_user_id` -- "nobody owns it, so anyone may manage it" -- which is
  exactly backwards for a corpus that has no owner *because it belongs to the
  deployment*. `IndexedFileSummary.can_manage` is answered by the same predicate
  the write endpoints enforce, so an offered button is a request that will be
  accepted.

  Worth knowing having found it: with `AUTO_INGEST_ENABLED` false (the default)
  there is now **no reachable path in the UI that indexes `docs_path` at all**.
  Uploads land in `uploads_path` and are managed normally; the shared corpus is
  a deployment concern, and pretending otherwise was what produced the dead
  buttons.

- **Two claims in Technology Stack were false**, and both would have sent a
  reader the wrong way about the degraded embedding directly above:
  "Sentence-Transformers BGE-M3 embeddings" (there is no bi-encoder embedding
  path at all -- `sentence_transformers` is imported only for `CrossEncoder`, by
  the reranker and NLI) and "Claude Haiku ... in `image_processor.py`" (that
  path was deleted on 2026-09-05, as this file records elsewhere).

**Open, and deliberately not fixed in this pass: the analytics dashboard has no
producer.** `RetrievalLogger.log_retrieval` has **zero callers in `app/`** -- the
only occurrence is its own `def`. So `/app/analytics` (total queries, success
rate, average response time, agent distribution, document ranking, and both
export buttons) reads a deque nothing ever appends to, and reports zeros
forever. The top-bar metrics strip reads the same endpoint and is therefore
permanently hidden, which is why its carefully-argued "renders nothing until
there are samples" guard has never been seen to do anything.

Two reasons it is a decision rather than a patch. There are already two metrics
systems -- the `request_rows` ring the middleware writes, which works and feeds
the ops SLOs, and this one, which does not -- and a duplicate is the shape this
file keeps deleting rather than feeding. And `RetrievalLog.question` stores the
**raw question text**, which `export_logs` writes into a downloadable CSV: wiring
it as-is would build exactly the question-text store `question_ref()` exists to
prevent. If it is wired, the field carries a digest.

#### The analytics dashboard has a producer (2026-09-09)

`RetrievalLogger.log_retrieval` had **no caller anywhere in `app/`** -- the only
occurrence in the tree was its own `def`. So `/app/analytics` reported 0 queries,
0% success and 0ms forever, both export buttons produced an empty file, and the
top bar's metrics strip stayed permanently hidden behind the "render nothing
until there are samples" guard this file describes at length as a considered
design. It had never had samples and could not have.

`record_query_analytics` (`api/routes/internal/pipeline_contract.py`) is the
producer, called from the query endpoint beside `record_grounding_support`.
Four decisions in it are the point:

- **The question is stored as a digest, never as text.** `RetrievalLog.question`
  held the raw string and `export_logs` writes rows into a downloadable CSV, so
  wiring it unchanged would have built exactly the store `question_ref()` exists
  to prevent -- and **nothing in the dashboard ever read that field**. It is
  `question_ref` now, which keeps the one property the export needs: the same
  question yields the same handle, so rows can be correlated.
- **`filtered_docs_count` was deleted rather than filled.** It had no reader and
  no honest source -- there is no separate agent-filter stage to count -- and the
  only plausible value was `retrieved_count` again, which is a number that looks
  measured and is not.
- **It cannot fail a request.** Analytics is a by-product of answering; the whole
  builder is wrapped, because an answer that was produced must not be lost
  because a counter could not be updated.
- **The timing key was wrong in the first version and would have shipped a zero.**
  It read `stage_durations_ms`; `summarize_workflow_execution` emits
  `stage_latency_ms`. Every row's retrieval time would have been 0, which the
  dashboard displays as a fast retrieval -- the exact "reports something other
  than what ran" this function exists to undo, reintroduced one key deep.
  `test_the_timing_key_is_the_one_the_diagnostics_emit` pins it **against the
  producer**, not against the test's own fixture, because a fixture that invents
  the key lets the builder read nothing and still pass.

Verified end to end rather than by unit test alone: one real question, then the
dashboard reading `TOTAL QUERIES 1`, `AVERAGE RESPONSE TIME 19203ms`,
`Retrieval: 4630ms`, `general: 100%`. That query had failed to find evidence, and
the row said `has_result: false` and the page said `SUCCESS RATE 0%` -- correct,
and the first evidence that the panel now reports rather than decorates.

**And the message that reported it was wrong twice over** (fixed the same day).
`SYNTHESIS_FALLBACK_MESSAGE` -- "抱歉，当前答案生成服务暂时不可用" -- was returned
from **13 sites** covering a synthesis timeout, an LLM error, an empty
completion, and *having no evidence to answer from*. The last is the most common
failure on an installation with an empty corpus, and it sent the reader to an
administrator when what they needed was a document or a web search; the model
was answering perfectly. `synthesize_candidate` **already tagged that branch
`no_evidence`** -- the code knew the cause and the string did not say it.

It was also **Chinese only**, in an application whose reason for existing is
that it works in both languages, with `detected_language` in scope at every one
of those sites. So an English speaker hitting any of the thirteen got a Chinese
sentence about the wrong thing.

`synthesis_fallback(reason, language)` replaces it, and `is_synthesis_fallback`
replaces the `text == SYNTHESIS_FALLBACK_MESSAGE` comparison that
`synthesize_candidate` used to detect the state -- a state inferred from
user-facing text stops being correct the moment the text varies, which this
change makes it do. The constant survives as the zh generation-failure string
because one orchestration test names it; new code calls the function.

#### Local embeddings are semantic when the model is present (2026-09-09)

`MODEL_BACKEND=local` -- what a fresh checkout runs -- had exactly one embedding
option: `LocalHashEmbeddings`, blake2b hash buckets whose own docstring says
"for offline/dev RAG smoke use". Vector search therefore matched on little more
than exact overlap, which is the largest single quality ceiling in the system,
and the console correctly called it `degraded`. Meanwhile the Technology Stack
section claimed "Sentence-Transformers BGE-M3 embeddings" and had for a long
time -- there was no bi-encoder anywhere, `sentence_transformers` being imported
only for `CrossEncoder`. A reader hitting the degraded embedding would have gone
looking for a misconfiguration rather than a missing feature.

`LocalSemanticEmbeddings` + `_load_local_embedder` (`services/models/runtime.py`)
close it, copying `_load_cross_encoder` deliberately:

- **`local_files_only=True`.** A model that was never downloaded returns `None`
  and the caller falls back to hash buckets. Without it the first query on a
  fresh machine starts a multi-gigabyte download inside a request, with no
  timeout and no breaker -- the defect this repository already fixed once for the
  NLI stage.
- **Synchronous.** Every caller reaches embeddings from a worker thread, and
  nothing reached from `asyncio.to_thread` may drive an event loop.
- **The console reports which one is running**, not which one is named.
  "Configured" and "present on this machine" are different facts and only the
  second changes an answer; `local_embedding_backend()` answers the second, and
  the degraded message names the model that is missing.

**Changing the embedder requires a reindex, and the store now says so.** A Chroma
collection is dimension-locked -- hash is 384, bge-m3 is 1024 -- so an existing
store fails every query after a switch. Chroma's own message names two integers
and no remedy, which reads as a corrupt database to somebody who has just
changed a setting; `_as_dimension_mismatch` turns it into one that names the
reindex, keeps the original text, and deliberately leaves every non-dimension
error alone rather than swallowing all failures as this one.

**Getting the model onto a machine here needs a mirror.** `huggingface.co`
answers, but `cdn-lfs.huggingface.co` does not resolve from this network, so a
download stalls at 0 bytes on the weights after fetching 36K of metadata --
which looks like a hang rather than a DNS failure. `HF_ENDPOINT=https://hf-mirror.com`
is the drop-in; ModelScope is reachable too.

#### Simulating a user found four more (2026-09-09)

Every one came from operating a surface, and none is visible to a check that
measures the code against itself.

- **Five agent cards stayed English when the UI switched to Chinese.**
  `AGENT_MODES` carried English `title`/`desc` literals and `AgentWorkbench`
  rendered them straight, so the sidebar around them translated and they did
  not -- in an application whose reason for existing is that it works in
  Chinese. `i18n/locales.test.ts` scans for LITERAL `t("...")` calls and these
  went through none, which is the `KeyboardHelp` shortcut list and the
  `IntegrationsPanel` class names again in a third guise. The fix is a switch of
  ten literal keys rather than `t(`agentModes.${mode.key}.title`)`, because an
  interpolated key is invisible to that same scan.

- **There were FOUR upload format lists, not two.** The `accept` fix recorded
  above missed `SUPPORTED_CHAT_RE` and `SUPPORTED_DOC_RE` in `useFileUpload` --
  the regexes that decide what is actually *kept* -- because the guard checked
  `accept=` only. **Widening the composer's `accept` to all fifteen therefore
  made it offer files the very next line discarded without a word**, which is
  worse than the state it replaced. There really are two sets: a question is
  asked *about* a document you look at, and a corpus is loaded in the Knowledge
  Base. `lib/uploadFormats.ts` derives both accept attributes and both matchers
  from two lists, the guard asserts the subset relation, and it now catches a
  regex copy as well as an attribute.

- **A rejected file was dropped silently unless every file was rejected.** Each
  caller tested `if (!files.length)`, so a `.docx` dropped beside two PDFs
  uploaded the PDFs and lost the third with no message. `partitionUploads`
  returns the rejected names and the notice says which -- and the three messages
  were hardcoded English, now `chat.upload.*`.

- **The sentence-grounding hedge was being spliced into filenames.** Observed in
  a real answer:

  ```
  ... (如 config.基于当前可用证据，py、settings.基于当前可用证据，yaml ...)
  ```

  This is the defect class CLAUDE.md records as fixed on 2026-09-05, in a form
  that fix could not cover: `_ABBREVIATION_RE` protects "Dr." and "pp.", and a
  filename is not an abbreviation -- there is no list of extensions to keep up
  with. `_INLINE_DOT_RE` states the property instead: **a dot between two
  alphanumerics is not a sentence boundary in either language this system
  writes**, since an English sentence ends with a dot plus a space or nothing
  and a Chinese one ends with "。". `config.py`, `settings.yaml`,
  `app.services.models` and `v1.2.3` are all covered by one rule.
  `tests/services/test_sentence_grounding_inline_dots.py` asserts both
  directions, because a protection that is too broad stops splitting real
  sentences and scores a whole paragraph as one claim -- worse than the defect,
  and silent.

Both halves of that answer's other defect were fixed the same day -- the
duplicate reference list and the `<URL_7>` inside it. See the redaction section
below.

#### A redaction token must not reach the reader (2026-09-09)

The model is shown `<URL_7>` in place of a URL and **writes it back**. A real
answer ended with the model's own reference section listing `[1] <URL_7>`,
directly above the pipeline's list showing the actual link.

`OutboundRedactedChatModel` restores the values in the reply now.
`redact_messages_with_restorer` hands back the payload and a closure, and **the
mapping never leaves that one call** -- which is the point rather than an
implementation detail. A per-request ContextVar or a module-level map would work
equally well and would risk the one failure that actually matters here: one
user's values resolving inside another user's answer. A cosmetic token is worth
far less than that, so most of
`tests/security/test_redaction_is_restored_in_the_reply.py` is about the
boundary rather than the substitution.

Three details:

- `_RedactionState` now records the value **as written**. `seen` is keyed on the
  normalized form (URLs and emails are lower-cased so one address in two casings
  gets one token), and restoring from that key would hand a reader
  `https://example.com/docs/x` where the document said `Docs/X` -- a URL path is
  case-sensitive.
- Longest token first, so `<URL_1>` cannot eat the prefix of `<URL_11>`.
- **The streaming path is deliberately not restored.** A token can straddle a
  chunk boundary and half of one substituted is worse than the whole of one left
  alone; the fragments are a draft the frontend replaces with the answer from
  the query response, which comes through `invoke`.

**The duplicate heading was a second defect**, and `strip_model_reference_list`
removes a reference section the model wrote for itself before `output_filter`
appends the authoritative one. It is conservative on purpose -- only at the end
of the answer, only when every line after the heading is a bracketed entry,
bounded to forty. A model that wrote prose under that heading keeps it: losing
an answer's last paragraph to a tidy-up is far worse than one repeated heading.

#### Web search finds five results and keeps none, by design

Chased because two questions in a row answered "没有找到可以用来回答的资料"
while `search_web` returned five results in three seconds when called directly.
The chain, measured:

```
total_results 5 -> filtered_results 5 -> final_results 0
"No results passed quality filters (min_score=0.5)"
```

`WEB_DOMAIN_ALLOWLIST` **ships non-empty** -- eleven entries -- and in allowlist
mode `_source_score` returns 1.0 for a listed host and **0.0 for everything
else**. So `arxiv.org`, `en.wikipedia.org` and `*.gov` pass while `veso.ai`,
`thequery.in` and `blog.csdn.net` do not. That is why some questions that day
answered with web citations and some found nothing: it depends entirely on which
domains DuckDuckGo happened to return.

This is a trust policy working correctly, not a bug, and widening it is an
operator's decision. What was wrong is that **nothing said so**: the warning read
only "No results passed quality filters (min_score=0.5)", which does not
distinguish a throttled search engine from an allowlist doing its job -- and
those need opposite responses. It names the rejected hosts and the setting now.

**`WEB_MIN_SOURCE_SCORE` is inert on a default installation.** Its value (0.2) is
read only in the `else` branch, and the allowlist branch is taken whenever
`WEB_DOMAIN_ALLOWLIST` is non-empty, which it is by default -- that branch
hardcodes `min_score = 0.5`. The hardcoding is harmless in itself (scores there
are only 1.0 or 0.0, so any threshold in between behaves identically), but a
setting that reads 0.2 and cannot apply is the shape this file keeps recording.
It is left as-is and documented rather than "fixed" by threading the setting
into a branch where it would change nothing.

#### A user pass over the surfaces nobody had opened (2026-09-09)

Session rename, pin, `Ctrl+N`, `Ctrl+B`, `Ctrl+K`, `?`, the prompt library and
the architecture page all work. Two things did not, and both are the shape this
file keeps recording -- a write nobody reads, and a sentence that describes
something other than what runs.

- **A saved display name never came back.** `PUT /auth/profile` persists it
  correctly -- verified straight out of SQLite -- and returns it, because that
  response is built from a `SELECT` inside the writing transaction. But
  `SessionManager.get_user_by_token` joins `auth_sessions` to `users` and selects
  `role`, `status` and `credit_balance` from `users` while **not selecting
  `display_name`**, so the dict handed to `AuthUser(**user)` had no such key and
  the model default filled in. `GET /auth/me` therefore reported `None` for
  everyone, always, and the profile page said "个人资料已保存" and showed the old
  value on reload.

  The write half working perfectly is what let this survive: the endpoint's own
  response looked right. `tests/api/test_profile_display_name_round_trip.py`
  reads it back through a **second** service with its own connection, so
  "committed" and "echoed inside the transaction" cannot be confused.

  `get_user_profile` omits the column too and was **left alone**: its two callers
  want existence, role and the approval token, and adding a column nothing reads
  is what this repository removes. A first draft of the test asserted otherwise
  and was corrected -- the test was wrong, not the code.

- **Session search could never find a session.** `POST /sessions` writes a
  session to `HistoryStore` and **no `SessionMetadata`**; the only writers of
  metadata are the edit-metadata endpoint and session import. `POST
  /api/v1/sessions/search` reads `SessionMetadata` alone, and its text query
  matches `description` -- `SessionMetadata` has no title field at all. So on an
  ordinary account every search returns `{"results": [], "total": 0}` while two
  sessions sit visible in the sidebar, and the panel answered "No sessions found
  -- try adjusting your search criteria or filters".

  The plumbing is coherent: it is a metadata search, not a session search.
  Making it a session search means merging two stores with pagination and
  scoring across both, which is a design change rather than a correction. **The
  sentence was what was wrong**, and it now names what is searched and the tab
  that fills it.

**Two things checked and deliberately not changed.** The profile page shows
"不限" for an administrator's credits against a `credit_balance` of 10 -- and
`reserve_chat_credit` really does exempt them (`AND lower(role) <> 'admin'`), so
the page is right. And `get_user_profile`, above.

**Two of my own diagnoses were wrong and are worth recording**, because both
looked like application defects and were the automation: `computer.key` needs
`Enter`, not `Return`, and `?` does not arrive as `shift+slash`. Dispatching a
real `KeyboardEvent` proved the command palette and the shortcut sheet were fine
in both cases. The rule from the contrast auditor holds for input too -- check
the instrument before filing the finding.

### Technology Stack

**Backend**: FastAPI + LangChain
**Vector Store**: ChromaDB (local, persistent)
**Graph Store**: Neo4j (optional)
**Database**: SQLite only. Each store opens its own `sqlite3` connection
(`app/services/auth/auth_service.py`, `app/services/sessions/history.py`,
`app/services/sessions/metadata_db.py`, `app/services/prompts/store.py`,
`app/wiki/store.py`, `app/retrievers/stores/vector.py`,
`app/services/connectors/{metadata_repository,repository}.py`). There is no shared connection
pool and no PostgreSQL support: an async SQLAlchemy pool existed but was never used by
any business code and was removed on 2026-08-29, along with the `asyncpg`/`aiosqlite`
dependencies. `DATABASE_URL` **still exists** as a `Settings` field and is still read, by
`app/services/sessions/metadata_db.py::_get_db_path` — but only the `sqlite:///` form is
honoured, and anything else falls back to `./data/querymind.db`. That fallback used to be
silent, which is how `deploy/compose/compose.yaml` came to hand the backend a
`postgresql+asyncpg://` URL the application ignored; it logs a warning now, and the compose
entry is gone.
**Frontend**: React 18 + TypeScript + Vite + Zustand (state) + i18next (i18n)
**Models**: a chat model per the administrator's configuration or `MODEL_BACKEND`
(OpenAI, Anthropic incl. relays, DeepSeek, Ollama, or the offline
`LocalEvidenceChatModel`); embeddings from a local sentence-transformers bi-encoder (`LOCAL_EMBED_MODEL`,
default `BAAI/bge-m3`) when the model is present, hash buckets when it is not,
or OpenAI/Ollama when an administrator configures one;
`sentence-transformers` **CrossEncoder** for reranking (`BAAI/bge-reranker-v2-m3`)
and NLI validation. This line used to name Claude Haiku for "multimodal image
description in `app/services/multimodal/image_processor.py`" -- that path
(`_call_claude_vision`) was deleted on 2026-09-05, as this file records two
sections down, and captioning goes through `app/ingestion/extraction/vision.py`.
**Deployment**: Docker Compose with deployment scripts in `deploy/scripts/`. The `postgres`
service is behind the `with-n8n` profile, because n8n is the only thing that uses it — the
backend is SQLite-only, and gating its startup on a database it never opens bought nothing.

## Development Patterns

### Working with the Current Architecture

**Understanding the codebase**:
- Services in `app/agents/*Service` are **adapter wrappers** around existing implementations
- The actual logic is in modules like `app/agents/router/routing.py`, `app/agents/synthesizer/generation.py`
- Services provide cleaner interfaces but delegate to these legacy components

**When modifying functionality**:
1. **For interface changes**: Modify the `*Service` class in `service.py`
2. **For logic changes**: Modify the underlying implementation modules
3. **For new features**: Decide if it belongs in the adapter or the implementation

**Architecture guidelines**:
- Keep services stateless
- Use typed contracts (`RouteDecision`, `EvidenceBundle`, `FinalAnswer`) for communication
- Avoid adding more configuration constants unless absolutely necessary
- Consider if logic should be algorithmic vs. configuration-driven

### Quality Metrics

Monitor these when modifying retrieval or synthesis. **Each target now names what
measures it, and says "nothing" where nothing does** — three of the four had no
measurement behind them at all, which makes a number a wish rather than a claim (the same
principle as the `advanced-rag/config` fix).

| target | measured by |
|---|---|
| **Router accuracy** >95% | **nothing.** No labelled routing set exists. |
| **Citation completeness** >90% | **nothing** as an aggregate. It is *enforced* per answer by the cascade's citation stage, but never scored across a query set. |
| **P@5** >0.85 | **not comparable** — see below. `make eval-retrieval` reports P@5 and MRR over a tracked corpus, but that corpus has one relevant document per query. |
| **Latency P95** <5s | `build_ops_alerts`, from the `request_rows` ring the middleware writes. Process-local, so a restart empties it. |

**The retrieval numbers come from `make eval-retrieval`** (`scripts/eval_retrieval.py`,
`app/evaluation/retrieval_eval.py`, added 2026-09-04), which runs a tracked bilingual
micro-corpus through the **real `KnowledgeOrchestrator`** with a BM25-only strategy.
Through the orchestrator rather than through `app/evaluation/baselines/`, because those
baselines call `similarity_search` directly and never touch the orchestrator, the
adapters or `reciprocal_rank_fuse` — they cannot observe a change to any of them. BM25
only, because `read_corpus_records` reads a plain JSONL file, so it needs no embedding
model, no Chroma, no Neo4j and no LLM, and therefore runs on a fresh checkout.

**P@5 on the shipped set is capped at 0.2 and that is not a bad score**: every query names
exactly one relevant document, so at most one of five retrieved items can be relevant.
Reading it against a 0.85 target quoted for a multi-gold corpus is a category error, and
`tests/evaluation/test_retrieval_metric.py` pins it precisely so nobody makes it from a
metrics table. **MRR is the metric with headroom here, and what is pinned is the per-query
rank map, not the aggregate** — BM25 over a fixed JSONL is deterministic, so it is asserted
rather than ratcheted, per query, so a failure names the query. Every query ranks its gold
document first except `q-15`, which ranks second by the lexical limit described above, so
MRR is **0.9688**. This paragraph claimed 1.0 until 2026-09-05: it was written before the
CJK tokenizer commit added that limit and was not corrected with it.

`KNOWN_LEXICAL_LIMITS` and `expected_ranks` live in `app/evaluation/retrieval_eval.py`
because `scripts/eval_retrieval.py` needs the same answer. It did not have it: its exit
code was `score.mrr == 1.0`, so `make eval-retrieval` returned **1** on the state the suite
asserts is correct, from the tokenizer commit until this one. A command that reports failure
on a correct state teaches people to ignore it, which is the same defect as a metric that
cannot fail, reached from the other side. The comparison is exact in both consumers, so an
*improvement* is reported too — reaching rank 1 there means the entry should go.

**The vector and hybrid paths stay a manual command, not a CI gate**, and the argument is
sharper than the one for `npm run screenshots`: `_load_cross_encoder` uses
`local_files_only=True`, so a CI runner without the model silently degrades to
`lexical_rerank` and would publish a number measuring the lexical fallback rather than the
reranker. A green metric measuring the wrong thing is worse than no metric.

Before trusting any of this, note the test that matters most:
`test_a_mismatched_scope_returns_nothing`. `mask_evidence` runs inside `_retrieve_source`,
so a corpus whose ownership metadata does not match the scope drops every item and scores
0.00 for reasons unrelated to retrieval — indistinguishable from a broken retriever.
Proving the metric can fail is the precondition for believing it when it passes.

Two limits that remain: the corpus is 15 synthetic rows over 16 queries, so it exercises tokenisation,
fusion and scoping rather than real-world ranking; and `data/eval/retrieval_corpus.jsonl`
plus `data/eval/retrieval_queries.json` override the tracked defaults (first existing path
wins, the same shape as `_BENCHMARK_QUERY_PATHS`) for a deployment that wants to measure
its own corpus.

### Code Organization

**Backend Structure**:
- `app/pipeline/` - Public API entry point (`RAGPipeline`)
- `app/orchestration/` - Execution coordination and flow control
- `app/agents/<component>/` - Component implementations with service adapters
  - `service.py` - Adapter interface for orchestration
  - Other files - Actual implementation logic
- `app/domain/` - Shared contracts and types
- `app/api/` - FastAPI routes and HTTP layer
  - `app/api/routes/public/` - Public-facing endpoints
  - `app/api/routes/admin/` - Admin-only endpoints
  - `app/api/routes/operations/` - Operational/health endpoints
  - `app/api/routes/internal/` - Contracts shared between route modules, never registered as routers
- `app/retrievers/` - Retrieval implementations (vector, BM25, hybrid)
- `app/core/` - Core configuration and utilities

**Internal APIs**:

`app/api/routes/internal/pipeline_contract.py` exposes the standard RAG pipeline
execution contract used by:

- `admin/ops.py` - Performance profiling and benchmarking
- `public/sessions.py` - Message rerun functionality

Note (2026-08-29): this module and the live chat/SSE routes previously lived in
`app/api/routes/compatibility/`, whose name implied deprecated code and repeatedly
misled readers. The chat endpoint moved to `public/query.py`, the SSE endpoint to
`public/orchestration.py`, and this contract to `internal/`. No HTTP path changed.

**Frontend Structure**:
- `frontend/src/pages/` - Page components (ChatPage, LoginPage)
- `frontend/src/features/` - Feature-specific logic
- `frontend/src/stores/` - Zustand state management
- `frontend/src/services/` - API clients
- `frontend/src/i18n/` - Internationalization (zh/en)

**Note**: The `app/agents/` directory name is historical - it houses components, not autonomous agents.

### Frontend styling (rewritten 2026-09-07)

**The frontend is shadcn/ui components over Tailwind v4, in a warm amber theme.** The
visual language is ported from a design prototype (`QueryMind NextGen`): a 56px glass top
bar, a 320px glass sidebar, frosted content cards on an "aurora" wash of four soft amber
pools, 12px body text, and mono for every number, id and filename.

This replaced the previous strategy -- "new UI in Tailwind, migrate the 73 hand-written
stylesheets as they are touched, never in bulk". That strategy was right while the target
was the existing look; it is the wrong shape for a change of visual language, because the
two palettes then coexist for as long as the migration takes. The estate went from 79
stylesheets / 15,781 lines to 9 / 1,194.

**The cascade order still exists and is still what makes any of this work**, declared once
in `styles/main.css`:

```
theme      Tailwind's token layer, then core/theme-amber.css
legacy     core/reset.css (the preflight) and components/charts.css
components component-local CSS imported from a .tsx
design     core/elevation.css and core/surfaces.css
utilities  Tailwind, and the @utility classes in core/app-utilities.css
```

`legacy` has two occupants now rather than 73, and both are there because they must
outrank nothing and be outranked by utilities. Keep the statement even so: it is what
lets a stylesheet be added and migrated away again without an arms race.

Unlayered rules beat every layer regardless of specificity, which is why nothing may be
imported without naming a layer -- with one deliberate exception, `core/app-utilities.css`,
whose `@utility` rules Tailwind places in `utilities` itself.

**Tailwind v4, CSS-first, and no config file.** Theme values live in `@theme` / `@theme
inline` in `main.css`; there is no `tailwind.config.js` and no `components.json`. Two v4
specifics that a v3-era tutorial will get wrong: custom utilities use `@utility`, not
`@layer utilities { .x {} }`; and Radix enter/exit animations come from **`tw-animate-css`**,
because `tailwindcss-animate` is a v3 PostCSS plugin that cannot load here.

**The `tw:` prefix is gone.** `tailwind-merge` parses class names against Tailwind's own
conflict table and does not understand a prefix, so with one configured `cn()` degrades
silently from "the later class wins" to plain concatenation -- which is the entire reason
`cn()` exists. Dropping it required deleting `core/utilities.css` in the same commit: it
hand-defined 19 classes sharing names with real utilities (`.rounded-md` = 8px vs
Tailwind's 6px, `.shadow-sm`, `.text-primary`, `.bg-surface`, ...) and `utilities` outranks
`legacy`, so every one would have flipped appearance with nothing reporting it.

**`components/ui/*` is written by hand, not by the shadcn CLI.** The CLI writes
`components.json`, assumes no prefix, and may emit v3-shaped files that fight the existing
`@theme inline` block. Each component is `React.forwardRef` (React 18 -- not the React 19
ref-as-prop form) + `cva()` + `cn()`.

Two lint shapes are forced by `--max-warnings 25`, which is a ratchet that sits at exactly
25 with no headroom:

- **Variant tables live in a sibling file** (`button.tsx` + `buttonVariants.ts`).
  `react-refresh/only-export-components` allows constant exports but `cva(...)` is a *call
  expression*, so a component file that also exports its variants costs one warning each.
  The repo already used this shape in `animations/animatedButtonVariants.ts`.
- **Radix re-exports are declared as real function components**, not
  `export const Dialog = DialogPrimitive.Root`. The rule cannot tell a value re-export is a
  component. This is also what current shadcn/ui upstream does.

#### The amber palette does not clear WCAG AA as published, and the theme corrects it

Measured, not eyeballed -- as a fill carrying white text and as text on white are the same
number:

```
amber-500 #f59e0b   2.15  fails
amber-600 #d97706   3.19  fails   <- the prototype's primary
amber-700 #b45309   5.02  passes  <- the smallest step that works
amber-800 #92400e   7.09  passes
```

So the prototype's primary button (`from-amber-500 to-amber-600` + white text), its active
tag chip and its `stone-400` metadata are all below AA. Rather than change the hue, the
theme splits amber **by role** -- which is why `core/theme-amber.css` has three amber
tokens where the prototype had one:

| token | value | may be used as |
|---|---|---|
| `--brand` | `#b45309` | a fill carrying white text (5.02) |
| `--brand-text` | `#92400e` | amber ink on a light ground (6.79-7.09) |
| `--brand-accent` | `#d97706` | icons, borders, the glow -- **never text** (3.05) |

`--brand-accent` keeps the prototype's exact hue, so the parts of the design that read as
"amber" are unchanged; only ink and fills moved. Two exemptions are deliberate and allowed
by 1.4.3: `--brand-mark-gradient` (the bright ramp, used only behind the logo glyph and the
assistant avatar -- a logotype) and `--text-faint` (placeholders only; darkening one makes
an empty field look filled).

**The aurora is what makes the flat-page number the wrong one to measure.** `--text-muted`
was `stone-500 #78716c`, which is 4.59 on `--bg-page` but **4.16** where the aurora pools
are strongest -- and that wash sits behind every surface. It is `#6e6762` now: 4.82 on the
darkest point, 5.32 on the flat page, 5.56 on a card.

#### Where the design and the platform disagree

Four things bit during the rewrite; each is the kind that fails silently.

- **`core/critical.css` outranks everything, including `utilities`.**
  `vite-plugin-inline-critical` inlines it into `<head>` with `order: 'post'`, so its
  `<style>` lands after Vite's stylesheet link, and nothing in it is layered -- an unlayered
  declaration beats every cascade layer. Its `body`, `html`, `*` and `#root` rules therefore
  cannot be overridden by any class: `<body className="aurora-bg">` loses silently. That is
  why the aurora is painted there (which is better anyway -- the warm ground is up before
  the stylesheet loads) and why its token block is a **second copy** that must be changed in
  step with `theme-amber.css`. It also only applies in a **build**; `apply: 'build'` means
  dev renders whatever `theme-amber.css` says, so the two disagreeing shows up only as a
  flash on a cold production load.
- **Element-level legacy rules reach the new components.** `components/buttons/*` styled the
  bare `button` element with `display: inline-flex; white-space: nowrap`. Utilities outrank
  `legacy`, but only for properties they *set* -- a class list that never mentions either
  property does not win, which is what collapsed the sidebar's agent cards onto one
  overflowing line. Those sheets had to be deleted, not merely stopped being used.
- **Deleting them removed the app's only preflight.** Tailwind's `preflight.css` is not
  imported here; `core/reset.css` is the preflight. A utility like `border` sets
  `border-width` and expects `border-style` to already be `solid`, so `reset.css` now
  carries the `*, ::before, ::after { border-width: 0; border-style: solid }` reset. Without
  it Chromium's UA defaults showed through: a dark inset frame inside every amber field and
  a grey box around every link-styled button. Caught by `npm run screenshots`, not by any test.
- **An element rule beats inheritance.** `reset.css` used to set `color` on `h1`-`h6`. A
  heading on the brand gradient inherits `text-white` from its parent -- except that rule
  won, and put dark ink on the amber CTA banner at 2.82:1 with nothing in the markup to
  explain it. Headings inherit their colour now.

#### Two elements drawing one focus ring

The login field showed **three concentric amber marks** on focus, and it had since the
rewrite. Measured on the wrapper and the input together:

```
wrapper  border   1px  rgb(217,119,6)              focus-within:border-brand-accent
wrapper  ring     2px  rgba(217,119,6,0.2)         focus-within:ring-2
input    ring     3px  rgba(217,119,6,0.2)         core/surfaces.css, on the ELEMENT
```

`core/surfaces.css` gives every `input, textarea, select` a `:focus-visible` ring, and
that rule is right: `reset.css` is this app's preflight, so an unclassed field would
otherwise show focus not at all. What it cannot know is that the field is a *bare* input
inside a bordered wrapper which already shows focus -- so both draw an affordance for one
control, one outside the border and one inside it.

`@utility field-shell` (`core/app-utilities.css`) is the fix, on five wrappers:
`AuthInput`, `SessionSearch`, `TagInput`, `SessionList`'s filter, and the composer
capsule. The wrapper is the field a reader sees, so the wrapper keeps the ring and the
control gives its up. **It wins by layer order, not specificity** -- the element rule
scores (0,4,1) against this rule's (0,2,1), and it does not matter, because `@utility`
output lands in `utilities` and surfaces.css sits in `design`. That is the same mechanism
this file already describes for buttons, used deliberately instead of accidentally.

**The `Input` primitive was never affected, and why not is the general rule.** It carries
its own `focus-visible:ring-2`, which sets `box-shadow` from the `utilities` layer and so
already overrode the element rule -- verified by putting its exact class string on a live
page and clicking it: one 2px ring, accent border, nothing doubled. The defect belongs to
the *bare input inside a styled wrapper* shape, not to inputs generally.

`fieldShell.test.ts` (7) asserts every `field-shell` site still carries a focus
affordance of its own, parametrized per site. Moving a ring must never remove one: a
field with no focus indicator is worse than the ugly one it replaced, is a WCAG 2.4.7
failure, and is invisible to anyone using a mouse.

**Three separate diagnostics said "there is no focus styling here", and all three were
wrong.** Worth more than the fix, because each looks authoritative:

- **Walking `document.styleSheets` with `r.cssRules ? recurse(r.cssRules) : [r]` drops
  every leaf rule.** A plain `CSSStyleRule` has a `cssRules` that is *empty but truthy*
  (CSS nesting), so the walk recursed into nothing and returned nothing. It reported zero
  `focus-within` rules in the whole document -- i.e. that the wrapper's focus styling was
  inert -- when the build plainly contains them. Recurse only when `cssRules.length`.
- **Reading `getComputedStyle` immediately after a click catches `transition-all`
  mid-flight.** The wrapper read as its unfocused border colour. This is the transition
  trap this file records for the contrast auditor, reached from the other direction: there
  a frozen intermediate invented a failure, here a frozen *start* value hid a real one.
- **Programmatic `.focus()` on an off-screen element does not match `:focus-visible`.** A
  probe positioned at `left:-9999px` measured a field that was focused and not
  focus-visible, so it reported no ring at all. Put the probe on screen and click it.

The measurement that settled it did all three correctly -- correct walk, 400ms settle,
real click -- which is also how the fix was verified: `inputRing: "none"`, wrapper ring
intact.

**And a 400ms settle is still not enough.** Sweeping the rest of the controls onto one
focus idiom, a `<select>` read `--brand-border` where the input beside it read
`--brand-accent`, from the same class string, both matching `:focus-visible` -- a
`transition-colors` still running from the previous focus. That is the fourth reading this
one trap has spoiled in a day. **Disable transitions for any computed-style measurement,
not only for the contrast audit**, which is the rule this file already gives one section
down and which is strictly better than waiting:

```js
const kill = document.createElement("style");
kill.textContent = "*{transition:none!important;animation:none!important}";
document.head.appendChild(kill);
```

With it, the input and the select agree: accent border, one 2px ring, nothing doubled.

**One focus idiom, everywhere but one file.** `:focus` fires on a mouse click and
`:focus-visible` is the browser's judgement that somebody is navigating by keyboard;
twelve files still used the first, so clicking a field in the admin console rang and
clicking one in the settings drawer did not. 25 occurrences across `focus:ring-2`,
`focus:ring-[var(--brand-ring)]`, `focus:border-brand-accent`, `focus:outline-none` and
`focus:ring-0` moved. `components/ui/dropdown-menu.tsx` keeps the plain form deliberately:
Radix moves focus programmatically for its roving tabindex and `:focus-visible` does not
match that, so a menu item styled with it would stop highlighting as you arrow through.

The risk in that sweep was a control that used to show focus on click and now shows
nothing. Measured rather than assumed: **Chrome matches `:focus-visible` on a
mouse-clicked text input**, so those are unchanged; a `<select>` does not, and there the
popup opening is the feedback. `fieldShell.test.ts` pins both directions -- no `focus:`
ring, outline or border utility outside that one file, and the menu still using it, so the
rule cannot pass by matching nothing.

#### Fonts are self-hosted, and must stay that way

The production CSP is `font-src 'self' data:` in all three copies
(`app/api/transport/middleware.py`, `frontend/public/_headers`,
`frontend/nginx-security.conf`). The prototype's `@import url('https://fonts.googleapis.com/...')`
would be blocked -- silently, with the page just falling back to a system face. Inter and
JetBrains Mono come from `@fontsource*`, which emits local woff2. Inter has no CJK coverage
and this app is bilingual, so `--font-sans` lists Noto Sans SC directly behind it and the
browser falls back per glyph; Latin renders in Inter and Chinese in Noto within one run of
text.

#### Shape, depth, and the ratchet

`--shape-control` 8px / `--shape-card` 12px / `--shape-panel` 16px / `--shape-pill`, and
`--elev-1..3`, defined in `core/elevation.css` and mirrored into `@theme inline` so
`rounded-card` and `shadow-elev-2` exist as utilities. **Do not delete `elevation.css`**: it
is both the source of those five utilities and the design-scale ratchet's escape hatch.

`npm run lint:design` is a ratchet over `.css` files only -- Tailwind classes in `.tsx` are
invisible to it, so migrating a sheet drives its count to zero. Two rules that point in
opposite directions: **deleting a stylesheet is free** (the check iterates `current` and
looks the baseline up as a dictionary, so a stale entry is never visited -- the opposite of
the Python side's `KNOWN_OFFENDERS`), but **moving one is not** (the new path is compared
against `{0,0}`, so every literal in it counts at once). The baseline went from 53 files /
135 radii / 191 shadows to 1 / 1 / 4.

#### A class name that matches no rule

`IntegrationsPanel` rendered as raw browser defaults -- unstyled fields, bullet
lists, a bare `<h2>` -- inside an otherwise finished settings drawer, from the
2026-09-07 purge until 2026-09-08. It carried `integrations-panel` and
`runtime-panel-empty`, and the sheets defining those were among the 73 deleted.

**Nothing reported it, and nothing could have.** A class name matching no rule is
invisible to eslint, to `tsc`, to the tests, to `lint:design` (which reads `.css`
only) and to the contrast audit (which measures what *is* painted). It survived a
whole change of visual language and two contrast passes. This is
`core/surfaces.css` from the other side: that sweep found 28 of 39 selectors
matching no element, and this is an element carrying a name no selector defines.

`npm run lint:classes` (`frontend/scripts/check-dead-classes.mjs`) closes it, and
runs in CI **after the build**, because the question can only be asked of what the
browser receives: `dist/assets/*.css` plus the critical CSS inlined into
`dist/index.html`. It found 8 names; six were vestigial labels on elements
Tailwind already styled completely (`chat-window`, `toast-stack`, `profile-page`
...) and were removed, and two were the real defect.

Four things about building it are worth more than the finding:

- **Ask the build, not the stylesheets.** Most class names here are utilities no
  `.css` file declares, so "grep the stylesheets" answers the wrong question.
- **The inlined critical CSS is part of the answer.** `vite-plugin-inline-critical`
  never emits it as an asset, so reading `dist/assets/` alone reports
  `app-loading` -- which `core/critical.css` really does define -- as dead. A
  blind spot in a dead-code finder is how a live rule gets deleted.
- **Tailwind escapes the dot in a fractional utility** (`gap-1.5` is
  `.gap-1\.5`), so the first port compared against raw text and called the entire
  spacing scale dead: 34 findings, all wrong. The delivered CSS has its
  backslashes stripped before matching.
- **Collect class names from `className` positions, not every string literal.**
  The first version matched any hyphenated literal and reported 134 hits --
  package names, model ids, `aria-*` attributes, DOM ids, ReactFlow edge ids,
  `cva` variant keys. A list that is 95% noise gets skimmed once and ignored.

And the one that matters most: **narrowed to `className`, the second version read
`className="a b"` by searching the already-unquoted value for QUOTED strings,
found none, and scanned 198 tokens instead of 386** -- so it reported the two
names known to be dead as clean. A scan that silently stops matching makes every
later assertion pass. It is verified against a planted class each time it is
changed, the same rule this file applies to the contrast auditor and the
sensitive-content gate.

The rewrite that followed is what the panel should have been: `Input`, `Label`,
`Badge` and `Button` primitives, the same `<details>` + count badge shape as the
memory panel beside it, and `IntegrationsPanel.test.tsx` (7) where there had been
no test at all. Its five fields had each carried the same 200-character class
string copied inline, already drifted from `components/ui/input.tsx` -- `focus:`
where the primitive uses `focus-visible:`, and no height.

**Two things the browser found that no static check would have.** The connector
rows showed list markers: the memory panel escapes them only because its `<li>`
happens to be `display: flex`, which is incidental, so both lists say `list-none`
now. And a test asserting the form trims its input could not pass --
`pattern="[a-z][a-z0-9_-]{0,63}"` is implicitly anchored, so a padded id fails
constraint validation and the handler's `.trim()` never runs for that field. The
code was right and the test was wrong; it says so where it types a clean id.

The audit over both panels: **47 nodes, one failure at 2.08** -- the `Test` button
of a *disabled* connector, which is WCAG 1.4.3's inactive-component exemption and
the same category as the four disabled pagination buttons already recorded. Both
enabled ones measure 5.28.

#### Verifying a visual change

`npm run lint`, `type-check`, `lint:design`, `test`, `build`, `lint:classes` is what CI
runs (the last after the build, which it needs). Two things it
does not, and this kind of change needs both:

**`npm run screenshots`** -- eight states, run before and after and compared as a pair. It
needs `SHOT_PASSWORD` for a real account: without it the run dies on
`waiting for locator('.page-shell')`, because the sign-in fails and the shell never
mounts. That error names the selector, not the credential, so it reads as a broken
selector when it is a missing password. It
earned its place again here: the missing preflight border reset above was visible in the
first capture and invisible to all 56 tests. It hard-codes six selectors, all of which the
rewrite deliberately preserved: `.page-shell`, `.page-shell.sidebar-collapsed`, `.sidebar`
and its `.open` class (read with `classList.contains`, because a panel translated
off-canvas still reports as visible), and the accessible names `sessions and tools`,
`sign in`, `collapse all` / `expand all`, plus the `Username` / `Password` placeholders.
Rename any of those and update the script in the same commit.

**A contrast audit in a real browser** (`frontend/scripts/contrast-audit.js` -- paste it into
the console of the FRONTED tab, then `__probe()` before believing `__audit()`), measuring
resolved colours rather than reading CSS.
The three traps this repo already recorded all make an auditor report a PASS it has not
earned -- `color-mix()` computes to `color(srgb r g b / a)` and not `rgba()`; `opacity` is
not in `getComputedStyle().color` and has to be multiplied down the ancestor chain; and a
background tab does not advance CSS animations.

**A fourth turned up here, and unlike the others it reports a FAILURE that is not there.**
A non-painting tab does not advance CSS *transitions* either, and does not fire
`requestAnimationFrame` at all. An element caught mid-transition keeps its intermediate
computed value forever: the sidebar's backdrop read `opacity: 0` while open, and the
enabled New-session button read `opacity: 0.5` -- a leftover from the `disabled:opacity-50`
it had while sessions loaded, frozen by `transition-all`. Both looked like real 2.35:1
failures and survived a nine-second wait and a full reload. What settles it is that
*no CSS rule matching the element sets that value*; what fixes it is forcing a paint --
taking a screenshot -- immediately before measuring. Do that per page, every time.

Report what was *skipped* too: a count of nodes checked is the only thing that separates
"clean" from "did not look". And prove the scanner can fail before believing it -- planting
three probes (a plain low-contrast node, amber on its own `color-mix` tint, and a node
dimmed only by an ancestor's `opacity`) is what showed the first version was silently
skipping the second.

After the fixes: **514 nodes across six pages, zero failures**, and a second pass over the
rewritten console on 2026-09-07 -- **1,356 nodes across its ten tabs, zero non-exempt
failures** -- plus the categories checked by hand because the scanner skips a gradient
backdrop: white text on `--brand-gradient` (5.02 and 7.09 at its two stops), the
architecture diagram's five ReactFlow node types (worst 4.59), and the eight-to-nine nodes
per admin tab that sit directly on the aurora, which are `--text-main` or `--text-muted`
and are covered by the measurements above.

**Two more traps turned up the moment the console adopted `glass-card`, and both were
fatal to the audit rather than to the app.**

- **A translucent surface sends the walk to the page ground, and the ground is a
  gradient.** `glass-card` is `rgba(255,255,255,0.98)` -- alpha under 1, so compositing
  continues past it, reaches the aurora and bails. The whole console became unmeasurable
  the instant it started using the design's own surface: 4 nodes checked on the landing
  page against 122 skipped. The aurora is RESOLVED now rather than bailed on. Each pool is
  `radial-gradient(circle at X% Y%, C 0%, transparent N%)`; CSS sizes an unqualified
  `circle` farthest-corner and the alpha falls linearly to the N% stop, so the four can be
  evaluated over a grid and the darkest pixel used as the base.

  **The first attempt at that was wrong in the expensive direction.** Compositing all four
  pools at full alpha gives `rgb(251,216,142)` and reports `--text-muted` at 4.05 -- a
  failure. No pixel has that colour; the pools sit at four different corners. Solving the
  gradients properly gives `rgb(252,235,203)` and 4.74, which passes. A worst case that
  cannot occur generates work that did not need doing, and would have darkened a token for
  nothing.

  Keying the bail-out on `body` is also not enough: `LandingPage` paints the same aurora on
  its own `.landing-root`, which skipped 84 of that page's 88 nodes. The check is on the
  gradient, not the element.

- **A non-painting tab never settles a transition, and waiting does not fix it.** The
  console's tab pills read `rgb(152,147,144)` -- between white and `--text-muted`, set by
  no rule -- through a nine-second wait, a full reload and a forced paint. Disabling
  transitions and animations for the duration of the audit is what settles it; every
  element then computes the value a reader actually sees. That is strictly better than the
  "force a paint first" advice this file used to give.

Two real findings came out of the second pass. An `aria-hidden` ellipsis in the pagination
was painted in `--text-faint` at 2.52 -- `aria-hidden` hides text from a screen reader, not
from a reader. And `surfaces.css` was still focusing every unclassed control with
`rgba(79,70,229,0.12)`, indigo, from the palette this theme replaced; it is an ELEMENT
selector, so it reached exactly the controls carrying no Tailwind ring of their own.

After both passes: **1,387 nodes across the console's ten tabs, 88 on the landing page, 91
on architecture, 86 on the deck, 30 on analytics -- zero non-exempt failures.** Exempt: four
disabled pagination buttons. Skipped and hand-checked: white on `--brand-gradient` (5.02 and
7.09 at its two stops) and the 34 ReactFlow diagram nodes (worst 4.59). One real finding came out of it and is worth stating as a rule: **an alpha
tint of a colour has no fixed contrast**, because what shows through it depends on what is
behind. `.admin-state-icon` paired `color-mix(in srgb, var(--success) 16%, transparent)`
with `color: var(--success)` -- 4.82 over white, but 4.34 over the aurora wash the console
actually sits on. The opaque `--success-surface` / `--warning-surface` / `--info-surface`
tokens exist for exactly this pairing and do not move.

**What not to reach for.** No CSS-in-JS runtime and no second component library. Do not add
a pixel-diff CI gate -- without a pinned font stack and a seeded corpus it fails on the day
someone upgrades Chromium, not the day the UI breaks. Do not "fix" a cascade problem by
re-freezing the design baseline.

#### Migrating a stylesheet is not adopting a design

The console was moved off hand-written CSS on 2026-09-07 and **the first pass got
the wrong half of the job**. It rewrote the console's OWN visual language in
Tailwind -- the sci-fi corner bracket on every panel, a status dot on every KPI
label, an amber tick before every heading, `auto-fit minmax()` grids -- all
inherited from `admin/*.css`. Every check passed: the CSS was gone, the tokens
were amber, contrast was clean. And the console still did not look like the
design, because none of those ornaments are in it.

Measured against the prototype's admin view, which is the check that would have
caught it:

| | prototype | first pass |
|---|---|---|
| panel surface | `glass-card` x30 | 0 -- opaque `bg-surface` |
| corner bracket | none | on every panel |
| KPI tile | label / mono value / **note** (21 of them) | label / value, plus a dot |
| block heading | `text-xs font-bold uppercase tracking-wider` | the same, behind an amber tick |
| grids | `grid-cols-2 md:grid-cols-3 lg:grid-cols-6` | `auto-fit minmax()` x4 |
| header | ONE `glass-panel` bar holding title, subtitle and the tab rail | a `PageHeader` plus a separate tray |
| section root | a bare `space-y-6` stack of sibling cards | one outer panel, cards nested inside it |

**The rule: when the target is a new visual language, "which classes does this
element have" is not the question -- "which of the design's parts does this
element have" is.** `grep -c glass-card src/pages/admin` returns 0 and takes a
second; nothing in lint, type-check, tests, the design ratchet or the contrast
audit reports it, because every one of them measures the code against itself.

The second pass is what the table's left column describes. `AdminPanel` is
`glass-card rounded-card p-4` and nothing else; `KpiCard` gained the `note` line
and lost the dot; `SectionHead`/`SubTitle`/`AdminBlock` titles are plain
uppercase; the grids take a column count; `AdminPage` builds the one-bar header
itself and each section is a bare stack. `AdminPanel` survives for the one thing
that genuinely is a single card -- the prototype builds its Delegation form that
way -- and `AdminSystemMonitor` keeps a card per chart, which is that shape
already.

#### A help panel is a claim about the code

`KeyboardHelp` has listed `Ctrl+K`, `Ctrl+N`, `Ctrl+B`, `Ctrl+W` and `Ctrl+R` since it was
written. **None of them existed.** The only keydown handler in the whole frontend was the
one that opens that same sheet (`?` and `Ctrl+/`), plus `Ctrl+Enter` in the composer. Five
documented shortcuts, zero implementations, and nothing anywhere reported it -- a shortcut
that does nothing is indistinguishable from one you pressed wrong, which is why this
survived. It predates the 2026-09-07 rewrite; `git show HEAD:./src/components/KeyboardHelp.tsx`
has the same list and the same absent handlers.

Three are implemented now in `hooks/useAppShortcuts.ts`, mounted by `AppShell` so they work
on every signed-in route rather than on the chat page alone -- `?` used to work on one route
out of five, because the listener lived in the sheet and the sheet lived in `ChatPage`.

**`Ctrl+W` and `Ctrl+R` are deliberately not implemented and no longer documented.** The
browser owns them (close tab, reload) and a page cannot reliably take them back, so
promising them promises something the user experiences as the page eating a keystroke.
Their toggles live in the composer and the command palette instead.
`useAppShortcuts.test.tsx` asserts that pairing in both directions -- the keys that must
work, and the two that must be left alone -- and was verified able to fail by deleting the
`Ctrl+K` and `Ctrl+B` branches, which reproduces the pre-fix state exactly.

**The palette is the reason two of those keys are worth having.** `components/CommandPalette.tsx`
(cmdk, which was a dependency this rewrite installed and then never imported) puts the five
routes, the session list, the settings and session-management drawers, the shortcut sheet,
the language toggle and sign-out behind one keystroke. Nothing in it is new capability; what
was missing was any way to reach the chat-only drawers from the other four views.

**Both overlays are hand-rolled, so neither got dismissal for free, and one lost it in this
change.** `KeyboardHelp` implemented Escape inside its own key listener; moving that listener
into `useAppShortcuts` dropped Escape and nothing failed. cmdk's bare `Command` never had it
-- the string "Escape" does not appear in its bundle, since `Command.Dialog` is the wrapper
that handles dismissal. `hooks/useDismissable.ts` gives both Escape and focus restore, and is
pinned by test. It does **not** trap focus; if either overlay grows past a list of commands,
that is the point to reach for `@radix-ui/react-dialog` rather than to extend this.

**`Esc` was the sixth**, and the subtlest, because it half worked. The sheet called it
"clear input"; the handler called `onStop()` and only `while (isSending)`, so in the ordinary
case -- a half-typed question, nothing streaming -- the key did nothing at all, and in the
case where it did fire it did something other than what the row said. Both meanings are
worth having, so both are implemented and both are documented: Escape cancels the run while
one streams, and clears the draft otherwise. It claims neither when there is nothing to
undo, so a parent overlay can still take it.

**The guard is the point, not the six fixes.** `components/keyboardShortcuts.ts` is the
shipped list as DATA, and `keyboardShortcuts.test.tsx` fires every row of it at a live
handler -- `useAppShortcuts` on `window` for an `app` shortcut, the real `ChatComposer` for
a `composer` one -- and requires each to be claimed. A row added with nothing behind it
fails; a handler deleted while its row stays fails; and `BROWSER_OWNED` asserts the reverse
for `Ctrl+W`/`Ctrl+R`/`Ctrl+T`, which must be neither documented nor claimed. Parametrized
per shortcut, so a failure names the key. Verified able to fail by putting the `Ctrl+W` row
back exactly as it used to ship: two tests go red, one from each direction.

That is what was missing before. The documentation was a literal inside the component and
the handlers were in another file; there was no place where the two met, so nothing could
notice they disagreed for the entire life of the component.

`Shift+Enter` is the one row asserted the other way round: it is the textarea's own newline,
so what must hold is that nothing claims it.

One ordering detail worth keeping: `autoFocus` is applied by React during the commit, before
any passive effect, so a hook that records "what had focus before" in a `useEffect` records
the overlay's own input. The palette focuses its input from an effect ordered after
`useDismissable` instead.

#### What is left



The console was the last route on hand-written CSS and is now Tailwind like the rest
(2026-09-07). `styles/pages/` is deleted -- five sheets and their entry, 2,118 lines --
along with `core/tokens.css`, whose only remaining job was feeding them non-colour scales.
`src/styles/` is **nine files**: `main.css`, six in `core/` (theme-amber, critical,
reset, elevation, surfaces, app-utilities) and two component sheets kept on purpose.
This paragraph said "four files" until 2026-09-08, counting the groups rather than
the files -- worth naming, because the number a reader checks a claim against is the
one that has to be right.

The console's vocabulary lives in `pages/admin/components/`:

- `AdminPrimitives.tsx` -- `AdminPanel`, `SectionHead`, `SubTitle`, `AdminBlock`,
  `KpiGrid`/`KpiCard`, `TrendRow`, `TwoCol`/`OpsGrid`/`SectionBlock`, `ControlsRow`,
  `FilterGrid`/`FilterRow`, `AdminField`, `Hint`, `Muted`, `RowActions`, `StatePanel`,
  `StateIcon`, `CellStack`, `AuditBadge`, `AdminSkeleton`.
- `adminClasses.ts` -- the class *strings*: `ADMIN_FIELD`, `ADMIN_TABLE`,
  `ADMIN_TABLE_WRAP`, `ADMIN_TABLE_WIDE`, `ADMIN_CODE`, and the recharts chrome
  (`CHART_TOOLTIP` / `CHART_GRID` / `CHART_AXIS`, which were copied into five dashboards).

**They are two files for the lint reason, not a taste one.** `ADMIN_TABLE` is built by
`.join(" ")` -- a call expression -- and `react-refresh/only-export-components` lets a
component file export literal constants only, so each one in `AdminPrimitives.tsx` would
cost a warning against a budget that sits at exactly its ceiling. Same rule that already
splits `buttonVariants.ts` out of `button.tsx`.

**A table is styled by one class string of arbitrary variants**
(`[&_thead_th]:…`, `[&_tbody_tr:nth-child(2n)]:…`), not a wrapper component per cell.
Table styling is descendant styling by nature; a `<TableCell>` per `<td>` would have meant
editing several hundred cells across five tables to change nothing about the output. It
still lands in `utilities` and still merges through `cn()`.

**The user table's four sticky columns carry their `left` offsets as written-out
utilities**, beside the written-out widths they are the running total of. Two derived
numbers that must agree are worse than one pair sitting side by side.

**`core/surfaces.css` lost 28 of its 39 selectors in the same pass**, and that is the more
general lesson. It exists to apply the elevation language to class names a Tailwind class
list cannot reach, and it was written against the vocabulary of 73 stylesheets --
`.sidebar-module`, `.agent-mode-card`, `.session-item`, `.modal-content`, the `.admin-shell`
block. Nothing renders any of those now. What remains is the part that still has a job:
`input, textarea, select` as ELEMENT selectors (since `reset.css` is the preflight, an
unclassed field has nothing else to give it a shape), plus the five class names that are
behavioural hooks rather than styling -- `.page-shell`, `.bubble`, `.composer-panel`,
`.reactflow-wrapper` -- each styled from here because the rule reaches a descendant
or a container whose class list is assembled elsewhere, with `.page-shell` additionally
read by `scripts/screenshots.mjs`.

**The naive way to find those 28 says all 39 are alive**, because `grep -l 'card' src`
matches `KpiCard`. A class name has to be matched as a whole token inside a string literal,
and the literal is not always a `className=` attribute -- `cn()` takes bare strings, `cva()`
tables hold them, and a couple are built as `` `sidebar ${open ? "open" : ""}` ``. Collecting
every whitespace-delimited token of every string literal in `src/` over-approximates what
the app can emit, which is the safe direction for a deletion.

Five defects surfaced while converting, and every one is the same shape this file keeps
recording -- a rule that matched nothing:

- `AdminOpsDataTables` wrapped its two tables in `.audit-wrap` / `.audit-table`. Neither
  selector has ever existed; the sheet defines `.audit-table-wrap` and `.admin-audit-table`.
  Both tables had been rendering with no border, no header fill and no zebra since they were
  written.
- `AdminOpsDiagnostics` used `badge badge-success` / `badge-danger` / `badge-info`, whose
  sheet was deleted in the first pass of this rewrite -- so the modifiers were inert. They
  are `<Badge variant>` now.
- `AdminSystemMonitor`'s four recharts blocks carried a hardcoded cool-slate palette
  (`#0f172a` tooltips, `#334155` grid, `#94a3b8` axes) that the amber pass never reached,
  because it reads CSS files and these are JSX props.
- `exportUtils.tsx`'s CSV and JSON buttons were `className="secondary tiny-btn"`, a
  stylesheet deleted in the first pass of this rewrite -- so both had been rendering as bare
  text beside every export-capable dashboard. They are `<Button variant="secondary">` now.
- `surfaces.css`'s input focus ring was `rgba(79, 70, 229, 0.12)`, indigo, from the palette
  this theme replaced. It is an ELEMENT selector, so it reached every control carrying no
  Tailwind `focus:ring-*` of its own -- a range slider, a bare checkbox -- which is why a
  cool blue glow survived an amber sweep on exactly the controls nobody had focused.

`ChatTopbar.tsx` went with them: it was replaced by `TopNav` in the shell pass and left in
the tree with no importer.

#### Is the stylesheet migration finished?

Measured on 2026-09-08 rather than asserted, because three of the numbers in this file
had gone stale and one had never been right:

| | |
|---|---|
| stylesheets under `src/` | **9**, 1,194 lines (from 79 / 15,781) |
| class names in `src/` resolving to no rule | **0** of 379 (`npm run lint:classes`) |
| class selectors in those 9 files matching nothing | **0** of 29 |
| inline styles | **4**, every one a computed value |
| `components/ui/` primitives | 8 |
| `tailwind.config.js`, `components.json`, `tw:` prefix | none (the two `tw:` hits are comments *about* dropping it) |
| design-scale ratchet | 1 file / 1 radius / 4 shadows, all in `data-flow.css` |

So: yes, with the last three findings closed in that pass.

**`.topbar-menu-trigger` matched nothing, and three places said otherwise.** `ChatTopbar`
and `TopbarMenu` were deleted in the shell pass, taking the only element that carried it
-- but the rule stayed in `surfaces.css`, the comment above it named two readers, and it
sat in `check-dead-classes.mjs`'s escape list, which is the file whose job is finding
exactly this. The comment is the worst of the three: a reader checks it and stops.

One of those claimed readers had also stopped being one. `useSectionToggle` used to do
`querySelectorAll(".execution-trace-panel, .tool-approval-panel, .composer-panel")` and
now returns state; its own docstring says so. A comment naming a reader is a claim with a
shelf life.

**So the escape list now polices itself**: an entry naming a class `src/` no longer emits
fails the check. Same rule as `SECRET_BASELINE` and `KNOWN_OFFENDERS` -- an exemption list
can only shrink -- and verified by putting the stale entry back.

The third finding was one inline style that was not a computed value:
`style={{ borderRadius: "var(--composer-radius-inner)" }}` is a utility nobody wrote, and
is `rounded-[var(--composer-radius-inner)]` now, on the same element. That restores this
file's "every one a computed value" to being true.

**Two sweeps, opposite directions, and both are needed.** `lint:classes` asks "does this
class name resolve to a rule" and found `IntegrationsPanel`'s two; the selector sweep asks
"does this rule match anything the app can emit" and found `.topbar-menu-trigger`. Neither
sees the other's defect. The selector sweep is a scratch script rather than a gate,
because it over-approximates what the app emits on purpose -- the safe direction when the
output is "consider deleting this rule" -- and it reported `.animated` in `data-flow.css`,
which ReactFlow applies itself from `animated: true` on an edge. A finding list that needs
a human is not a gate.

#### What is not done

- `components/data-flow.css` keeps five categorical node colours for the ReactFlow diagram.
  Those are deliberately not amber: a diagram distinguishes node *types* by hue, and
  collapsing them to one brand colour would lose the distinction. All five clear AA with
  white text (worst 4.59).
- `components/charts.css` is one rule and cannot become a utility: recharts writes the
  series colour as an INLINE style on its legend label, and an inline style beats every
  cascade layer -- only `!important` reaches it.
- The design-scale ratchet is down to **1 file / 1 radius / 4 shadows**, all inside
  `data-flow.css`.
- `components/ui/` holds 8 primitives, not 19. Eleven were written because shadcn/ui ships
  them -- dialog, select, table, tabs, switch, checkbox, progress, scroll-area, separator,
  skeleton, tooltip -- and nothing ever imported one; they went on 2026-09-07 with the nine
  Radix packages they carried, plus `axios` and `framer-motion`, which had been unimported
  since before this rewrite. The check is one line and worth repeating before a release:
  a component is dead if no OTHER file imports its module, which is not the same question as
  whether its own file mentions it.
- `TopbarMenu.tsx` went with `ChatTopbar`, which the shell pass replaced and left in the
  tree with no importer.
- The eslint ratchet is 20, down from 25. Four of the five it lost were `catch (e) {}` with
  the binding unused; each is a deliberate silent catch and each now uses the optional catch
  binding, so the syntax says so rather than a comment. The comments were checked before
  being trusted -- `pinSession` and `deleteSession` really do report through
  `handleApiError` before re-throwing, so `SessionList` catching to reset a spinner is
  correct.

**The top bar's live readout is built, and what it took to make it honest is the point.**
The prototype's `Latency: 184ms` / `Cache Hit: 89.4%` is hardcoded demo text. This system
has no cache-hit metric, and the only figure available is the corpus-wide average from
`/api/analytics/overview` -- not "your last request", which is what a bare "Latency" in a
top bar reads as. So the labels say *average*, the second slot carries success rate, which
this system does measure, and the strip renders for admins only, because that endpoint is
gated on `ADMIN_OPS_MANAGE` and a control permanently empty for everyone else reads as
broken rather than absent.

**It renders nothing until there are samples, and that is the load-bearing line.**
`RetrievalLogger` answers an empty log with `avg_total_time_ms: 0, success_rate: 0`, which
rendered as "Success: 0.0%" in warning amber -- a bar telling every reader on every page
that the system was failing, when what it meant was that nobody had asked it anything. The
guard is on `total_queries`, not on the values, because no samples is not zero performance.
`TopNavMetrics.test.tsx` pins the empty case and the failed-fetch case; a decorative readout
must never be able to break the bar it sits in.

The prototype's separate Integrations button was deliberately not built: it is a second name
for a destination this app already has -- `IntegrationsPanel` is a section of the settings
drawer, which the palette opens.

**Thirteen translation keys were missing from BOTH locales.** i18next returns the inline
`defaultValue` when a key is absent, so the Chinese UI rendered the English string --
silently, forever, in an application whose reason for existing is that it works in Chinese.
Among them: all five top-bar view names, `auth.signIn`, `common.logout` and
`sessionManagement.title`, which the top bar had been falling back on since the shell pass.
`i18n/locales.test.ts` walks every literal `t("...")` in `src/` against both files and
checks three things -- every asked key exists in each locale, the two locales hold the same
key set, and no long Chinese value is byte-identical to its English one (a key copied rather
than translated). It opens by asserting the scan found at least 200 keys, because a scan
that stops matching makes every later assertion pass vacuously.

**36 literal inline styles were still hiding in two admin files and three error boundaries.**
`style={{ width: "60px", textAlign: "center" }}` on a `<th>` is a utility that was not
written; a bar's `width: ${pct}%` is data and stays. The three error boundaries were the last
surfaces on the palette this theme replaced -- `#007bff` buttons on `#f8f9fa` cards, written
as `var(--bg-primary, #fff)` pairs whose variables no longer exist, so what rendered was
always the fallback. They are the only thing a reader sees when the page they were on has
broken, and the amber pass had never reached them. Four inline styles remain in `src/`, every
one a computed value.

#### Two pre-existing defects found while verifying this

Neither was caused by the refactor; both were found by opening a surface that had not been
opened during it.

- **`/model-catalog` was never in the Vite dev proxy.** Vite's SPA fallback answered it with
  `index.html`, so the settings drawer parsed a web page as a model catalogue. Added to
  `vite.config.ts` alongside its `/app/`-prefixed twin.
- **`catalog?.providers[x]` guarded `catalog` but not `providers`**, so that malformed
  response threw and `ChatErrorBoundary` swallowed the entire chat page. Now
  `catalog?.providers?.[x]`. A drawer that cannot load its options should render without
  them, not take the page down.

### The query guard's Redis fallback could not catch a Redis failure

Fixed 2026-09-07, and found by running four chat queries at once: three returned
**500**, from `_within_user_rate` straight out through the endpoint. The guard has a
memory backend for exactly this, and five handlers documented as "Redis is not
answering, degrade to memory". Every one of them read
`except (ValueError, TypeError, OSError)`.

**None of them could fire.** `redis.exceptions.TimeoutError` and `...ConnectionError`
derive from `RedisError(Exception)`; neither is an `OSError`. The trap is worth naming
because it is the kind that survives review: **redis-py's `ConnectionError` shadows the
builtin, and the builtin *is* an `OSError`** -- so a reader asking "does `except OSError`
cover a connection error?" gets yes for the wrong class. `_redis_unavailable_errors()`
is now the one definition, resolved once and lazily so redis stays an optional install,
and `retrievers/hybrid/caching.py` already had the correct form
(`except redis.ConnectionError, redis.TimeoutError`) three directories away.

**Catching it was necessary and not sufficient.** `_effective_backend()` asks only
whether a client object exists, so a client that had failed every command was still
chosen: each later request paid the socket timeout again, and `stats()` -- which feeds
`/health` -- went on reporting `backend: "redis"` through an outage the guard was
silently absorbing. An operator reading that page during exactly this failure would have
been told the opposite of what runs. A failed command now takes the same path a failed
connection already had: `_drop_redis_client()` plus the cooldown. The outage costs one
timeout per cooldown rather than one per request, and `/health` says `memory` because
that is what is serving.

Two details in `tests/services/test_query_guard_redis_fallback.py` are load-bearing.
It patches the module's `_REDIS_CLIENT` rather than stubbing `_get_redis_client`, because
a stubbed getter keeps handing back the client the fix is supposed to drop -- the test
would pass on the broken code. And it asserts the count of handlers, five, because the
first sweep of that file found three by reading and missed two: four of five fixed looks
exactly like a complete change. Verified able to fail by restoring the shipped form --
seven of eleven go red.

**The zero-CPU hang this investigation started from did not reproduce.** `/health` had
stopped answering earlier in the day with the signature recorded under Common Issues
(process alive, 31 threads, no CPU, thirteen queued localhost connections, no outbound
socket), and the documented fix for it -- `_resolve_ddgs_eagerly` plus `_CLIENT_LOCK` --
is present in `app/tools/web/search.py`. Fifteen queries under `faulthandler.dump_traceback_later`
produced no wedge and no thread parked in ddgs, primp or `logging`. So the 500s were a
second, unrelated defect on the same endpoint, and the hang remains open: if it recurs,
the stack dump is the evidence to capture, `python -X faulthandler` plus
`dump_traceback_later(15, repeat=True)` being enough without adding py-spy to the
environment.

### Regular expressions

Sixteen patterns in this repository backtracked super-linearly (`S8786`, fixed
2026-09-03), and the fix has three shapes, in order of preference:

- **A negated class instead of a greedy `.`** -- `\|[^|\n]+\|` rather than
  `\|.+\|`. This is usually not a performance change at all but a statement:
  a table cell does not contain its own delimiter, and saying so removes the
  ambiguity the engine was exploring.
- **A bounded quantifier** -- `\s{0,8}` rather than `\s*`, the form the
  streaming redactor already used.
- **A possessive quantifier** (`[ \t]++`, Python 3.11+) where backtracking into
  the run could never succeed anyway, so the bound would be arbitrary.
- **A lookbehind forbidding a start inside the run** -- `(?<![.!?])[.!?]++\s+`.

**That last one is not a fourth flavour of the same idea, and reading it as one
is what left two patterns quadratic through the 2026-09-03 pass** (fixed
2026-09-09, found because SonarCloud went on flagging them). A possessive
quantifier stops the engine backtracking *within* one attempt. It does nothing
about that attempt being **restarted at the next offset**, and for a run of one
repeated character that is the whole cost: given `[.!?]++\s+` and n dots, the
engine starts at dot 1, swallows the run, fails on the whitespace, starts at dot
2, and so on. O(n^2), with no backtracking anywhere. Measured on
`app/ingestion/processing/coreference.py::split_into_sentences` and
`app/agents/synthesizer/citations.py::_tidy_spacing`:

```
              n=2000    n=4000    n=8000
possessive    11.2ms    30.0ms   138.9ms    x12.4 for a x4 input
+ lookbehind   0.04ms    0.08ms    0.15ms    x3.7  -- linear
```

Forbidding a start inside the run costs nothing, because the leftmost scan would
have taken the match at the front of the run anyway -- verified as identical
output over 4012 generated inputs before landing, which is the "diff the old and
the new" rule this section already gives. A dotted leader in a table of contents
is how a real document reaches the first one.

**Two of that rule's four findings were false positives and were left alone.**
`PATTERN_HEADERS` and `PATTERN_LISTS` (`app/agents/rag/config.py`) are anchored
`^...$` under MULTILINE, so the scan restarts only at a line start; measured,
they are linear. `tests/services/test_regex_scan_is_bounded.py` pins the two
real ones -- **not by timing**, which is a bad thing to assert on in CI, but by
the property that removed the cost.

**Its first version could not fail, which is worth more than the fix.** The
property test compiled a copy of the pattern written out as a constant in the
test, so deleting the lookbehind from the shipped code left it green: it was
asserting that its own string contains a lookbehind. It extracts the literal
from the module source and compiles *that* now. Verified by deleting both
lookbehinds -- four tests redden, where the first version managed two.

**Two of the sixteen were wrong, not merely slow, and for the same reason:
`\s` matches a newline.** Under `re.MULTILINE` that let a pattern anchored with
`^...$` reach past the end of the line it started on -- the clarification parser
paired a bare `-` on one line with a field name several lines below it, and the
lock parser could pick up an environment marker belonging to the next
requirement. Prefer `[ \t]` whenever the intent is "spaces within this line".

**Anything reading text a user or a document supplied is worth measuring rather
than reasoning about.** The clarification parser took 117ms on 800 lines of
whitespace and grew with the square; it takes 0.4ms now. But do not assert the
timing in a test -- a clock is a bad thing to assert on in CI. Assert the
property that removed it, which for both of these was "this matches within one
line".

Changing a pattern is a behaviour change until proven otherwise, and the proof is
cheap: run the old and the new against the same inputs and diff. That is how the
three structure detectors in `app/agents/rag/config.py` and the lock parser were
verified (60 inputs and 336 pins respectively, zero differences).

### Testing Strategy

`tests/` was cleared ahead of the v0.7 rewrite and is being rebuilt incrementally: each bug
fix lands with the regression test that would have caught it, rather than as a separate
back-filling effort. As of 2026-09-09 there are 1747 tests covering the chat round trip,
conversation context, graph routing, clarification, the async load guard, engine reuse,
answer safety, reader-facing citation numbering, stage-timeout degradation, the governed
tool stack with its multi-step loop and approve-then-resume cycle, retrieval
module-global isolation, connector persistence, streaming redaction, two-phase retrieval,
complexity- and plan-driven retrieval width, caller deadlines, skill-shaped synthesis,
follow-up completion, answer provenance, an answer that shows the reader none of the
machinery that produced it, a router cache that opens no event loop, a guard that every
Settings field has a reader, a guard that no module reads the environment behind
`Settings`'s back, the configuration-centre source with its three-step degradation, the
admin configuration surface with the writes it refuses, one vocabulary for audit actions,
an ASCII API document, a grounding SLO that measures answers, and the five functions
unpicked in the 2026-09-03 complexity pass -- document ingestion, the distributed query
guard, candidate collection, route selection, the document visibility rules and upload
storage, each characterized against its old implementation before being split, and the
regular expressions that backtracked super-linearly over user-supplied text, the
multimodal source that had never had anything to retrieve, and the sensitive-content gate,
whose suite is mostly negative assertions because a scanner reports PASS just as readily
when its checks match nothing, an offline retrieval metric measured through the real
orchestrator over a corpus that ships with the repository -- whose most important test
proves the metric can *fail*, since a scope mismatch scores 0.00 for reasons unrelated to
retrieval -- a graph triplet whose confidence records which extractor produced it, planner
sub-queries that reach the retrievers, per-query result lists that are interleaved rather
than concatenated before RRF, an NLI stage that runs off the event loop and scores Chinese
and reports which scorer ran, a governed read tool whose summary cannot carry an
instruction, one administrative view of a user rather than six copies of its SELECT --
whose derived columns are asserted to be derived, since `AdminUserSummary` defaults every
one of them to `False` and so cannot tell a dropped column from a false value -- a new
user's reported credit balance being the balance stored, a first run that creates an
administrator without shipping a password and without promoting whoever holds the name,
a model configuration that only an administrator can write -- pinned mostly by what must
*not* exist, since the per-user surface it replaced was inert for its whole life and only
its Test button ever appeared to work -- a record of the long-term memories
held about a user that is bigger than the working set one session is given and can be deleted
from any of them, and the China-specific PII
patterns that had never existed --
pinned by what each identifier is *called*, not only that it is caught, since three of them
were already caught under the wrong name -- and by an adversarial false-positive pass, which is
where all three defects in that change were found.

**That count is not 1236 independent assertions, and the number before it was stale.** Two
guards are parametrized one case per module — the audit-action scan over `app/` (367) and
the ASCII scan over `app/api` (59) — so they grow with the codebase rather than with
coverage, and **shrink with it**: the total fell from 1492 to 1483 across 2026-09-06 with no
test removed — deleting `app/api/utils/request_helpers.py` took one case from each scan, and
the eight further modules deleted that day took one each from the `app/` scan alone.
A drop in this number is not evidence that coverage was lost; check which suite moved. The real baseline on 2026-09-03 was 651, not the 538 this paragraph claimed:
the count had not been updated since 2026-09-02 while tests kept landing with fixes.
Parametrizing per module is deliberate — a failure names the file, and a new module is
covered the day it is added, where one test looping inside a single assertion reports the
first offender and stops — but it does mean this total is not comparable across the change
that introduced them.

`tests/security/` (746 of those, 367 being the per-module audit-action scan) pins the
user-data isolation invariants — see
`docs/superpowers/plans/2026-08-29-user-data-isolation.md`. That plan is complete
(phases 0-4) and all 8 of its `xfail(strict=True)` markers are cleared; keep using the same
pattern for a new gap, so a fix that makes the test pass fails the suite until the marker
is removed. `test_no_unrestricted_retrieval.py`
is a ratchet rather than a plain assertion: `KNOWN_OFFENDERS` records how many
unrestricted `similarity_search` calls each module has, and the count may only go down.
It is currently empty.

User questions must not reach the logs: `question_ref()`
(`app/services/observability/log_safety.py`) gives a stable digest instead, and
`tests/security/test_no_question_text_in_logs.py` enumerates every `logger.*` call via AST
to keep it that way. Truncating (`question[:50]`) does not count as redaction. Its
allowlist is keyed on `path::enclosing_function`; keying it on a line number made it
fail on any edit *above* an exempt call, which trains readers to re-point the entry
instead of asking whether a real leak appeared.

`test_streaming_redaction.py` tests the property, not the examples: for eight secret shapes
it asserts the streamed output equals the final redaction at *every* split offset, and that
what was already emitted is always a prefix of the final redaction. A chunk boundary is the
only thing that distinguishes streaming DLP from the batch kind, so a fixed set of chunk
sizes would test the wrong thing.

`pytest` is configured in `pyproject.toml` (`testpaths = ["tests"]`, strict asyncio mode).
CI runs it on every push and pull request (`.github/workflows/ci.yml`), together with ruff
and an OpenAPI endpoint census that fails if a refactor silently drops routers.

**The SonarCloud scanner in that workflow has never run** (checked 2026-09-05), and the
green "SonarCloud Code Analysis" check on every commit is **Automatic Analysis**, not it.
The step is `if: env.SONAR_TOKEN != ''` and no such secret exists, which is deliberate --
it was written to land dormant -- but three things follow that are easy to misread:

- **Coverage is not in SonarCloud and cannot be.** `api/measures/component` returns an
  empty array for `coverage`. Automatic Analysis cannot read a report, so
  `sonar.python.coverage.reportPaths` in `sonar-project.properties` is inert, as is
  everything else in that file. The `--cov-report=xml` step and the "Coverage total" line
  are real and go nowhere.
- **The New Code period is the whole repository**: `new_lines` is 89,411 against an
  `ncloc` of 82,875. Every gate condition is a new-code condition, so they are all
  effectively whole-project conditions. That is why one MAJOR bug in a fifteen-line script
  took `new_reliability_rating` to C and failed the gate on 2026-09-05 -- correct, and far
  more sensitive than "new code" suggests.
- Ratings are otherwise A across the board: **0 bugs, 0 vulnerabilities, 0 security
  hotspots**, against **370** code smells (96 critical) and ~44 hours of debt
  (re-measured 2026-09-09 from `api/measures/component`; this line read 570 and
  ~65h, which was the 2026-09-05 figure, and `ncloc` had drifted from 82,875 to
  73,461 in the same way).

**A finding is a question, not an instruction, and a third of the ones acted on in
the 2026-09-09 pass were answered "no".** Worth recording per rule, because each
wrong answer had a different shape:

- **`python:S125` (5 of 5 refused).** Every one is a **Chinese comment**, not
  commented-out code -- `# 密码已改但token轮换失败`, `# 安全修复：严格验证后才拼接PRAGMA语句`,
  `# kid:secret;`. The detector is trained on Latin-script code and reads a
  colon or a semicolon in CJK prose as syntax. Deleting explanatory comments in
  the one language this application exists to work in, to satisfy that, would be
  the worst trade in this file.
- **`python:S7504` (3 of 6 refused).** Each refused loop mutates what it
  iterates -- `del sys.modules[name]`, `self._last_seen_signatures.pop(key)`,
  `path.replace(target)` moving files out of the directory being globbed. The
  `list()` is what makes the loop legal; removing it raises `RuntimeError` or
  walks a directory being modified. The rule does not model mutation during
  iteration, so a sweep that "fixed" all six would have shipped three crashes.
  The three that stay now carry a comment saying why, naming the rule, so the
  next sweep does not have to rediscover it.
- **`python:S8786` (2 of 4 refused)** -- see Regular expressions above; the other
  two are anchored and measured linear.
- **`python:S8513` (2 of 8 answered differently than asked).**
  `model.startswith("gpt-4") or model.startswith("gpt")` is subsumed by its own
  second test, so the tuple form the rule asks for would have preserved a dead
  clause while going green. Both are `startswith("gpt")` now.

**And one finding was worth far more than the rule that raised it.** A
`python:S1481` on a discarded `token_ok` led to two functions named
`validate_and_check_approval_token` -- one in `app/api/deps/admin.py`, one in
`app/services/security/admin_security.py` -- **taking their arguments in
different orders** (`audit_callback` third against `action` third). Nothing
imported the first; all three admin call sites take the second. Dead code, but
the dangerous shape of it: writing the wrong order passes an action name where
the audit callback belongs, and it fails at the moment a refusal is being
recorded. Deleted, with
`tests/security/test_approval_token_has_one_definition.py` pinning that there is
one definition **and** that a rejected token raises rather than returning
`False` -- which is the property that makes discarding the boolean safe at all.
That is the same lesson this file already records for `python:S1192`: the
duplicated literal is rarely the defect, and reading the sites together is what
exposes one that is.

**`python:S3776` is measurable locally now**, which is the difference between
refactoring against a number and refactoring against a hunch.
`scripts/audit/cognitive_complexity.py` implements the scoring rules and
`--validate` checks itself against a SonarCloud issue export: it reproduces all
75 of the project's open findings exactly. Four rules were settled by
measurement rather than by reading the white paper -- comprehensions cost
nothing (74/75, against 48 for charging their `if` clauses), `try/else` costs one
while `finally` costs nothing (74/75, against 71 for charging both), and the one
worth knowing: **`elif x:` and `else:` holding a nested `if x:` produce the same
AST**, a lone `If` in `orelse`, and do not cost the same. Only `col_offset`
separates them, and getting it wrong was worth 8 points on one function.

It scores itself clean, which `reachability.py` did not -- that one landed as
three S3776 findings of its own. `test_the_scorer_does_not_trip_its_own_rule`
keeps it that way. **Target 13, not 15**, when refactoring against it: the tool
agrees with Sonar today, and leaving two points of headroom means a rule
difference cannot resurrect a finding.

**Five of the worst are done** (2026-09-09), each split along a seam it already
had and each **characterized against the implementation it replaced**, which is
this project's rule for a complexity refactor -- the argument from reading the
diff is what it exists to avoid:

| function | was | generated inputs | differences |
|---|---|---|---|
| `graph_lookup` | 50 | 600 graphs | 0 |
| `detect_entity_hallucinations` | 47 | 1506 answer/source pairs | 0 |
| `check_citation_support` | 40 | 4000 claims | 0 |
| `render_prometheus` | 39 | 800 metric states | 0 |
| `_extract_content` | 37 | 3005 payloads | 0 |

Total excess across `app/` went 666 -> 486, and 67 functions remain over 15.
Two details from those splits are worth keeping because a rewrite loses them
quietly: `render_prometheus` emits a TYPE line for a labelled histogram with no
samples and **nothing at all** for a flat one -- an asymmetry the shipped code
has and a scraper already parses -- and `_extract_content`'s per-shape helpers
must return None rather than `""`, so an empty block list falls through to the
next shape instead of answering with silence.

**The tool itself raised the project's only vulnerability**, which is worth
recording as a shape rather than an embarrassment. `pythonsecurity:S8707`: it
opened paths named inside a SonarCloud export (a network document) and the
export path from `--validate`. The first fix bounded the wrong half -- the paths
inside -- because that was the obviously-untrusted one; the sink the rule points
at was the argument. Both are bounded now, resolve-then-contain rather than a
`..` check a symlink defeats, and the containment sits at the CLI boundary
because putting it in the parser made the parser untestable without writing into
the working tree.

**The 2026-09-09 pass closed 71 findings and refused 12**, leaving 370 - 71.
Sonar measured 296 afterwards, and the gate went from failing to green. A second
pass took it to **262** (debt ~34h, from ~44h), and **found two real defects in
the memory store on the way** -- see below, because the rule that pointed at them
was a MINOR one about a character class.

The second pass in short: `python:S5778` eighteen of twenty (a `pytest.raises`
block that also builds its fixture can pass because the *constructor* raised;
the two left carry a comment saying the `raise` inside them IS the assertion),
`python:S8572` three (an `except` that logs without the traceback, all three on
startup paths nobody watches live), `python:S1854` two dead stores,
`python:S7500` three comprehensions that only copied, `python:S3358` two,
`python:S5869` two, `javascript:S7780` three, `typescript:S3863`,
`javascript:S6582`, and one `python:S1172` that was a cascade -- removing a
parameter left an unused one a level up.
Fixed: `S5713` (9), `S8513` (8), `S8409` (7), `S1172` (6), `S7773` (6), `S1066`
(5), `S6479` (5), `S3358` (8), `S8410` (4), `S1874` (4), `S1481` (4), `S7504`
(3), `S8786` (2). The untouched buckets and why: `S3776` (75) is a project, not
a sweep, and now has a tool; `S7503` (26) is the correct-but-unfixable set this
file already describes; `S6819` (18) wants `<dialog>` where `ConfirmDialog`'s
contract is deliberate and pinned by test; `S6353` (9) wants `\w` for
`[A-Za-z0-9_]`, and **`\w` matches CJK** -- the same trap that made the NLI
scorer read a whole Chinese clause as one token.

Turning the scanner on means adding `SONAR_TOKEN` **and** switching Automatic Analysis off
in SonarCloud -- the scanner refuses to run while it is enabled -- and deciding what New
Code should mean, since inheriting the whole repository as "new" is what makes the gate
behave the way it does. Those are three decisions, not one switch.

The frontend has vitest tests too: `src/**/*.test.ts` **and** `src/**/*.test.tsx`, run by
the `frontend` CI job, which also runs eslint (`--max-warnings 25`, itself a ratchet), `tsc`,
`npm run lint:design`, and the build. The `.tsx` half of that glob was missing until
2026-09-01, so every component suite was silently skipped — a component test cannot be
written in a `.ts` file. The default `environment` stays `node`; the two component suites
(`ExecutionTracePanel.test.tsx`, `ChatRuntimePanels.test.tsx`) opt into jsdom per file with
`// @vitest-environment jsdom`, rather than making the pure-logic suites — most of them — pay
for jsdom setup.

`pendingApproval.test.ts` pins that a governed action awaiting confirmation travels with
the question that produced it: ChatPage first tracked the question in a ref every
`ask` call site had to remember to set, and the clarification-complete path did not, so
confirming after a clarified query would have re-sent a stale question.
`storeReset.test.ts` covers the Zustand `reset()` that App.tsx calls on logout and on
any identity change: the stores outlive a logout, so a field added to a store but forgotten
in its `INITIAL_STATE` would show the next person on a shared browser the previous user's
data. The test discovers fields rather than listing them, so it catches that drift.
That suite is 147 tests across 18 files — small, and deliberately aimed at the things a
screenshot cannot check. `AdminConfigEditor.test.tsx` is the newest: it pins that a value
pinned in the process environment renders disabled, and that only edited fields are sent —
posting the whole form would turn a page load into a write of every value, and a stale read
into an overwrite. Note that auto-cleanup between renders only registers when vitest runs
with `globals`, which this project does not; a component test must call `cleanup()` itself
or every later query in the file finds two of everything.

Note: do not use `len(app.routes)` to count endpoints. FastAPI 0.138+ stores an
`_IncludedRouter` wrapper in `app.routes` instead of flattening child routes, so that number
varies by version. Count OpenAPI operations instead; the current baseline is 156 (CI asserts a >= 140 floor).
It read 153 until 2026-09-06 and had been 154 for some time before that — a number in this file that
nothing recomputes goes stale the way the test count did.

### Sensitive content gate (added 2026-09-04)

`scripts/check_sensitive.py` decides what may leave this machine. It runs in two places and
in three modes:

```bash
python scripts/check_sensitive.py                          # every tracked file (CI)
python scripts/check_sensitive.py FILE...                  # staged files (pre-commit)
python scripts/check_sensitive.py --tree DIR --expect N    # a delivery copy on disk
```

**The file list comes from `git ls-files`, not from a filesystem walk, and that is the whole
design.** A working tree legitimately contains `data/`, `logs/`, `internal_docs/`, `.venv/`
and `node_modules/` — all gitignored — so walking the filesystem would fail on every run and
be switched off within a week. Asking git instead turns the forbidden-path check into one
that means something: it fires on a `git add -f data/app.db`, which is how a database
actually reaches a repository.

Both hooks run it, and neither is redundant. The pre-commit hook blocks a secret **before it
enters history**, which is the only point at which removing one is cheap — once pushed, a
credential is compromised and the answer is rotation, not a revert. CI is the copy that
catches a `--no-verify` and a fresh clone where nobody ran `pre-commit install`.

**Nothing is rewritten automatically, and that is deliberate.** An auto-redacting commit hook
would mangle `tests/security/test_streaming_redaction.py` and `tests/services/test_answer_safety.py`,
whose fixtures *are* an AWS example key id, an `sk-` prefixed dummy and an OpenSSH private-key
header. A sweep that "desensitizes" the redaction feature's own test data breaks the security
suite, and does it in the worst possible way: after the suite has gone green. The gate reports
and blocks; a human removes the value.

Note that this section describes those fixtures rather than quoting them, and says "a Windows
user-profile path" rather than writing one. The first draft quoted all four verbatim and the
gate refused the commit — correctly. Adding `CLAUDE.md` to the baseline was the wrong fix: it
is long and edited constantly, so exempting it would mean a real key pasted here is never seen
again.

**The two baselines are ratchets, not allowlists.** `SECRET_BASELINE` (6 files) and
`LOCAL_PATH_BASELINE` (3 files) name individual files, not directories — exempting all of
`docs/` would have let a real key land in any document in the project. And on a whole-repository
scan, a baseline entry that no longer matches anything is itself a failure, so the exemption
list can only shrink. Same shape as `KNOWN_OFFENDERS` in `tests/security/` and
`scripts/design-scale-baseline.json`.

Three of those entries are the gate's own files, added after it refused the commit that
introduced them: the local-path pattern spells out git-bash's spelling of the Windows user
directory and therefore matches its own source, and the test cannot demonstrate that a
private-key header is caught without containing one. This paragraph was itself rejected once
for quoting that prefix — the gate is difficult to write about, which is a good sign.

**What it cannot catch**, which matters more than what it can:

- It matches *shapes*. A bare 32-character hex string, or a database password with no
  recognisable prefix, passes.
- It reads text files by extension allowlist. Anything inside a `.png`, `.pdf` or `.xlsx` is
  invisible to it — the eight tracked screenshots were checked by eye (they use the
  `walkthrough_alice` demo account and a public question).
- **It never looks at `.git/`.** History has to be audited separately. It was, on 2026-09-04:
  all 711 commits scanned for credential shapes and every hit was a placeholder
  (`NEO4J_PASSWORD=changeme`, an `sk-proj-` stub, the AWS documentation key), plus the
  once-committed `logs/web_activity/*.jsonl` (5 rows, all `test_user`/`Test query`, ip and UA
  `None`) and the once-committed demo corpus (`XX科技有限公司`). `internal_docs/` has never
  been committed.

#### Handing the whole folder to someone

Export with git; do not copy the folder and delete things afterwards.

```bash
git clone --no-hardlinks . ../querymind-delivery
python scripts/check_sensitive.py --tree ../querymind-delivery --expect 958
```

A clone contains only committed content by construction, so `.gitignore` — a rule this project
has already applied 700-odd times — does the filtering. "Copy, then `rm -rf` the sensitive
directories" is a denylist, and it misses `.venv/pyvenv.cfg` and `querymind.egg-info/PKG-INFO`,
both of which carry the developer's absolute path. Update `--expect` from
`git ls-files | wc -l`.

Two things learned doing this the first time:

- **Verifying the copy contaminates the copy.** Running ruff inside it left `.ruff_cache/`;
  running `pytest --collect-only` created `data/` — the exact directory name being excluded,
  produced by module import. `git clean -xfd` inside the copy is the fix (it cannot touch
  tracked files), and the final scan must come *after* every verification step.
- **A scanner that has never been proven to fail proves nothing.** Before trusting a PASS,
  point it at a directory holding a known secret, a `.db`, an env file with a value and a
  Windows user-profile path, and confirm all four trip and the exit code is 1. Doing that
  caught three defects in this script's own first draft, one of which — a regex where `\\+`
  had been reduced to `\+`, matching a literal plus sign — made every such path undetectable
  while the output looked entirely normal.

## Important Notes

- **Conda environment is mandatory**: Dependencies assume conda-managed packages
- **Do not commit** files in `.gitignore`: `internal_docs/`, `.env`, `data/chroma/`, logs
- **Document organization**: Use `docs/development/daily-logs/YYYY-MM-DD/` for daily work logs (create manually).
- **Bilingual system**: UI and responses support Chinese/English. Language detection is automatic via `language_analytics.py` (100% Chinese or 100% English, no mixing)
- **The OpenAPI document is ASCII**, pinned by
  `tests/api/test_openapi_descriptions_are_ascii.py`, which walks every `description=`
  keyword in `app/api`. The bilingual rule above is about prose shown to *users* — the
  Chinese and English question sets live in `app/agents/clarification/rules.py`; the API
  document is developer-facing and was already English in 80-odd places. The one router
  that was not had its bytes double-encoded (the UTF-8 encoding of a latin-1 misreading of
  UTF-8), so it served `å¼€å§‹æ—¥æœŸ` where the author typed `开始日期`. Nothing failed —
  a mangled description is still a valid string, and only a reader of the docs page would
  ever see it, which is why it survived. That was the only file in the repository in that
  state; the check is a whole-repo decode looking for character runs that round-trip back
  to CJK.
- **SSE streaming**: One subscription
  (`GET /api/v1/orchestration/executions/{execution_id}/events`, served by
  `app/api/routes/public/orchestration.py`) carries two event names. The query endpoint
  returns `metadata.execution_id`, which the client uses to subscribe.
  - `execution_event` — stage events, replayed from the tracker and `ExecutionEventStore`.
  - `answer_fragment` — the answer as it is written (added 2026-08-31, audit #14b).
    `SynthesizerAgentService._generate_streaming` publishes into the process-wide
    `AnswerStreamStore` (`app/orchestration/answer_stream.py`), bound to the execution by a
    ContextVar for the same reason the event store is: the engine is cached and shared, so
    instance state would file one request's fragments under another's id.

  **Fragments are a draft, and a separate event name so a client cannot mistake one for a
  finished answer.** They carry no citation numbering and no reference list — `output_filter`
  decides both, after the whole answer exists and after DLP has settled which citations
  survive — and internal `[E{k}]` markers are stripped rather than rendered. The frontend
  shows the draft in a `local-assistant-stream` bubble and replaces it with the answer from
  the query response.

  **There is a second streaming design in the tree, and nothing calls it — open technical
  debt, deliberately left in place on 2026-09-06.** `RAGPipeline.execute_stream` is declared
  on the `PipelineExecutionEngine` Protocol and forwards to
  `OrchestrationEngine.execute_stream`, which pumps an `asyncio.Queue` and yields
  `{"type": "status"|"done"}` dicts built by `_terminal_payload`. That is a different shape
  from everything described above: no `execution_id` subscription, no replay, and no
  fragment events — it emits stage status and then one finished payload. Nothing in `app/`,
  `tests/` or the frontend calls it, and `execute_stream` takes a `result_postprocessor` it
  immediately `del`s, which is the mark of an adaptation for a caller that has since gone.

  **It is not a DLP hole, and it is worth saying why rather than assuming either way.** It
  awaits `_execute` to completion and yields the resulting `FinalAnswer`, so `output_filter`
  — a `MANDATORY_STAGES` member — has already run; the `StreamingRedactor` is absent because
  nothing here streams unfinished text, not because anything skips redaction.

  It survived the 2026-09-06 dead-code sweep on purpose. Removing it touches the pipeline's
  public surface and a declared Protocol, so it is a design decision — pick one streaming
  design and delete the other — not the helper cleanup the rest of that sweep was. The cost
  of leaving it is a second answer to "how does this system stream", which is the shape of
  every duplicate that sweep did remove.

  **Nothing unredacted may enter that store.** `StreamingRedactor`
  (`app/privacy/streaming.py`) releases only text whose redaction cannot still change: it
  holds back a margin, cuts at whitespace, and confirms `redact(raw[:b])` is still a prefix
  of `redact(raw[:b + margin])` before releasing — a secret like `password = hunter2` begins
  *before* a boundary and crosses it, so a margin at the tail alone is not enough. What was
  emitted is tracked as a string rather than a length, because redaction changes lengths and
  offset arithmetic desyncs. Both redaction pattern sets had their whitespace quantifiers
  bounded (`\s*` → `\s{0,8}`) so a partial buffer cannot make a pattern scan unboundedly.
- **Answer quality telemetry rides the request's own metrics row**, not the audit log
  (wired 2026-09-03). `record_grounding_support`
  (`app/api/transport/middleware.py`) puts the answer's `support_ratio` on the row
  `request_timing_middleware` writes, and `build_ops_alerts` reads it from the same
  `request_rows` its p95 comes from — one window and one definition of "the last N hours"
  for both SLOs, with no new store, retention policy or schema. Before this the SLO
  averaged over audit rows with action `query.run`, which nothing writes, so an average
  over zero samples was **1.0**: a perfect grounding ratio published for a metric never
  once observed, and an alert structurally incapable of firing. Absence is now absence
  (`None`), which is a different claim from 1.0.

  **Not the audit log**, which is where the dead code pointed: its read path is
  `list_audit_logs(limit=2000)`, one window shared by every reader, and a row per query
  would flush every login failure out of it. Degrading the security audit view to feed a
  monitoring metric is the wrong trade.

  **The carrier is `request.state`, and it has to be.** The metrics row is written in the
  middleware's `finally`, after the endpoint returned; `request.state` is backed by the
  ASGI scope dict that `call_next` hands downstream and reads back. A ContextVar cannot
  do this — `call_next` runs the endpoint in its own task, so nothing it sets is visible
  up there, and the failure would look exactly like the `query.run` one: plumbing that
  reads empty forever. `tests/services/test_ops_slo_grounding.py` drives a real app
  through `TestClient` rather than asserting it in prose.

  Two limits, both already true of the p95 beside it: the ring is process-local, so a
  restart empties it and each worker sees only its own. Crossing that boundary is a
  time-series-database decision, not a change to these five lines.

- **Both Dockerfile stages install with `--no-install-recommends`**, and name
  `ca-certificates` explicitly rather than receiving it as a recommends of
  `curl` (`docker:S6500`). Dropping recommends without naming it would have left
  TLS trust resting on what the base image happens to ship, which is the sort of
  thing that works until the base image changes.
- **A convenience must never be able to fail a login** (2026-09-03). The login
  form's "remember me" stored the username through a module called
  `secureStorage`, which XOR'd it against a key hardcoded three lines above and
  base64'd the result. `btoa` throws above code unit 255, so a Chinese username
  threw inside the login handler's `try`, *before* `onLogin` -- the server had
  accepted the credentials, the exception was caught as a login failure, and the
  user saw a generic error that repeated until they unticked the box. In an
  application whose reason for existing is that it works in Chinese.
  `frontend/src/lib/rememberedUsername.ts` replaces it: a remembered username is
  a convenience, not a secret, so it is stored as itself, and every access is
  wrapped because a private window throws on read too. The lesson is not about
  base64 -- it is that the failure of something optional was inside the path of
  something that is not.
- **A backend that is briefly unreachable must not sign anybody out**
  (2026-09-09), which is the bullet above reached from the other side. `App`'s
  bootstrap called `/auth/me` and cleared the stored token in a bare
  `.catch(() => ...)` -- so a 500, a timeout, a sleeping laptop or a dev server
  being restarted destroyed the session. Reproduced by restarting the API under
  an open tab: the token was gone from `localStorage` afterwards and the
  password had to be typed again, for an outage that lasted seconds and said
  nothing about whether the session was still valid. Only a 401 does.
  `frontend/src/lib/sessionRecovery.ts::shouldForgetSession` is the rule, and it
  is a named function rather than a condition inside the `.catch` for the reason
  the shortcut list is data: inside the closure it was reachable only by
  rendering the whole app, so nothing could state it and "any error means sign
  out" survived. Keeping the token through an outage costs nothing -- there is
  still no user object, so the sign-in page renders either way -- and the next
  load once the server answers signs them straight back in.
  `sessionRecovery.test.ts` (8) asserts both directions, and 403 is deliberately
  in the *keep* column: a permission the account lacks is not a reason to end
  the session.

  **Verifying this in the browser reported the opposite of the truth first, and
  the reason generalises.** The verify-able-to-fail step had sabotaged
  `sessionRecovery.ts` to `return true` and restored it with `mv`; the Vite dev
  server kept serving the **sabotaged transform**, so a real browser against a
  real server measured the old behaviour on new code. Nothing looked wrong --
  the page rendered, the token vanished, the conclusion was "the fix does not
  work". `curl http://localhost:5173/src/<file>` is what settled it, and
  rewriting the file in place (rather than renaming one over it) is what
  invalidated the module. **A rename can slip past the watcher; ask the dev
  server what it is serving before believing a browser measurement of a file
  you have just restored.**
- **Third-party GitHub Actions are pinned to a commit**, not a tag
  (`githubactions:S7637`). A tag on somebody else's repository can be moved, and
  these steps run with the workflow's secrets. GitHub's own `actions/*` keep
  their major tags: nobody else can move a tag in that namespace.
  `tests/core/test_ci_workflow_is_loadable.py` enforces it, because the rule
  itself lives in SonarCloud and only runs after a push -- the feedback loop for
  a one-line mistake was a full CI run plus an analysis.
- **`evidence_dedup_key` returns `(kind, payload)`**, both two long. The two
  kinds are computed from different fields, so nothing but the kind keeps a
  content key and a provenance key out of each other's way in the same
  dictionary; a variable-length tuple with a discriminant at position zero only
  implied that.
- **`python:S7503` is 26 open findings** (re-measured 2026-09-05; it was 39, and
  the 13 that went were deleted code, not silenced rules). "async without await"
  cannot see a contract, and the ones that remain are the correct-but-unfixable
  kind the earlier count described: awaited normally, handed to
  `run_with_timeout` as a closure, awaited through a variable as a default
  callback, or gathered as coroutines. Do **not** re-derive that breakdown by
  counting `async def`s -- S7503 flags only those containing no `await`, which is
  a subset of each module's coroutines. Ask SonarCloud.

  What the earlier count called "the remaining 7" was the useful part: findings
  whose *classes* had no caller, where removing `async` would satisfy the rule
  and leave the dead code standing. That question is now answered.
  **`SmartChunker` and `ChartAnalyzer` are deleted** (2026-09-05).
  `ImageProcessor` and `TableExtractor` are constructed by `ingest_paths` and
  stay, and are now only what their one reachable method needs.
  `ingest_paths` calls `index_image` and `index_table`; the other 23 methods
  between them had no caller, and included a second OCR implementation, a second
  PDF image extractor, two table extractors, and `_call_gpt4v` /
  `_call_claude_vision` -- a direct-to-OpenAI vision path that would have been
  the unmasked one had anybody wired it. All deleted 2026-09-05, along with
  `ImageProcessor.__init__`, whose nine attributes `index_image` reads none of;
  that took `VISION_MODEL`, `ENABLE_OCR`, `OCR_LANGUAGES`, `MAX_IMAGE_TOKENS` and
  `ENABLE_TABLE_EXTRACTION` with it. Note what `ENABLE_OCR` was: a switch named
  for a feature it did not gate -- `app/ingestion/extraction/ocr.py` never read
  it. The same goes for `python:S7484` on
  `agent_tracking.py`'s SSE poll: no client calls that endpoint, and
  `AgentExecutionTracker` is `threading.Lock`-based, so an `asyncio.Event` there
  would need `call_soon_threadsafe` -- the defect class fixed twice already.
- **`python:S3776` is 89 open findings, and 85 of them are live code** (swept
  2026-09-06). The question was worth asking because the finding in
  `user_manager.py` was answered by `git grep`, not by refactoring:
  `UserManager.create_user` carried a complexity of 18 and had no caller
  anywhere -- `AuthDBService._create_user_record` is the live copy, left behind
  when it moved so it could share a connection with the OAuth identity insert,
  and the two had already drifted (only the live one has `raise ... from exc`).
  Refactoring it would have satisfied the rule and left the dead code standing.

  `scripts/audit/reachability.py` asks that question for every finding at once;
  `--sonar issues.json` cross-references a SonarCloud query. **Read its docstring
  before believing it**: it is a name-based call graph, so it over-approximates,
  and its first version reported two live HTTP endpoints as dead by resolving
  `from .export import router` in a package `__init__.py` against the package's
  parent. UNREACHABLE is a candidate to confirm with `git grep -w`, never a
  verdict, which is also why the script always exits 0 and must not become a CI
  gate.

  **The tool was itself three `python:S3776` findings** (35, 28, 21) for a day,
  because SonarCloud analyses `scripts/` too — a detail that also made the
  projected count after the dead-code sweep wrong: 89 − 6 cleared **+ 3 added by
  the audit script** = 86, not the 83 predicted. Fixed 2026-09-06 by extracting
  `package_of` / `resolve_relative` / `import_targets` out of `imports_of`,
  `_seed_roots` / `_propagate` / `_is_import_time_root` out of
  `_resolve_reachable`, and `dead_buckets` / `print_bucket` / `is_reportable` out
  of `report_dead`; the tool's own output over `app/` is unchanged in both modes,
  header line aside. A tool that adds to the backlog it exists to shrink is worth
  noticing early.

  **Progress on the live findings**, each verified by diffing the full output of
  the old and new implementations rather than by reading: 89 → 86 (dead code) →
  82 (`splitter.py` 58, and the audit tool's own three) → **79**
  (`agent_execution_tracker.py`: `get_quality_stats` 51, `get_execution_stats` 36,
  `track_agent_execution` 27 — the last of those because cognitive complexity
  counts a closure into its enclosing function, and its `async` and `sync`
  wrappers were 46 duplicated lines apart from two `await`s).

  **The tracker refactor exposed a divergence worth knowing about and did not
  fix it.** `/admin/agent-quality` and the agent-health endpoint label the same
  failed step differently: `get_quality_stats` clamps an error type to fifty
  characters and answers `"Unknown"` for an empty message, `get_execution_stats`
  does neither, and the two have always been able to group the same data under
  different labels. Unifying them changes what the quality dashboard shows, which
  is a decision with a visible consequence rather than a side effect of a
  complexity refactor — so `_execution_error_type` and `_quality_error_type` are
  two named functions whose docstrings say they differ on purpose, and
  `tests/services/test_execution_tracker_stats.py` pins both.

  Four findings were unreachable, and deleting them cascaded to two more whose
  only caller was one of the four: `extract_formula_relationships` and
  `extract_formula_semantics` (`extraction/formulas.py`), `split_wide_table` and
  `extract_nested_tables` (`extraction/tables_nested.py`), `merge_table_pages`
  with `is_table_start` and `extract_table_header` (`extraction/tables.py`), and
  `_require_existing_session_for_query` with `_latest_answer_for_same_question`
  (`api/deps/sessions.py`) -- 338 lines, four findings closed, no behaviour
  changed.

  **The cost of not knowing what is dead is already being paid.** `9120f987`, the
  commit before this one, named `_SINGLE_LETTER_VARIABLE_RE` in `formulas.py`
  because "two of its three uses produce the sets that the left and right of an
  equation are compared by" -- careful reasoning about a divergence that would
  "report a relationship that is not there", in two functions nothing called. All
  three uses are gone with them. The same commit's other half,
  `_SEPARATOR_ROW_RE` in `tables.py`, was written for three call sites and has
  one left; its docstring says so rather than continuing to claim three.

  **The second batch (2026-09-06) cleared `api/deps/documents.py` and three
  left-behind twins**, and two of them were worth more than the lines they cost.

  Nine of that module's helpers were unreachable and a tenth, `_source_mtime_ns`,
  was reachable only from one of the nine. Two of the nine were labelled
  "compatibility adapter for callers that still import the old API helper" -- with
  no such callers, and importing `app.orchestration.compatibility_post_execution`,
  a module `4994d7f3` deleted. They would have raised `ModuleNotFoundError`. **A
  function-local import is what hid that**: at module scope it would have failed at
  startup.

  One of them was the only writer of `AuditAction.QUERY_SOURCE_SCOPE`, so that
  member and its console filter option are gone too -- the "filter that can only
  ever return nothing" this file describes under Audit log vocabulary, arrived at
  from the other direction.
  `test_every_action_in_the_vocabulary_is_named_by_some_module` closes it:
  `test_the_console_filter_offers_actions_that_exist` checks only that the console
  offers nothing the enum lacks, and passes happily on a member nothing writes.

  The twins: `retrievers/hybrid/fusion.py::reciprocal_rank_fusion` beside the live
  `knowledge/fusion.py::reciprocal_rank_fuse`,
  `outbound_redaction.py::redact_text_for_provider` beside the live plural and
  `..._messages_...` forms, and `citation_grounding.py::_split_sentences`, whose
  name `_makes_a_claim`'s docstring gave as the function in the path when the
  caller is `_sentence_spans`.

  **Neither test-only definition was a test helper, and that is the useful half.**
  `_resolve_manageable_source_for_filename` was a back-compat wrapper no endpoint
  called, and the security test asserting an ambiguous filename refuses was the
  only thing keeping it alive -- so the refusal it proved was the wrapper's, not
  the resolver's. The wrapper is gone and the test asserts against
  `_resolve_manageable_document`. And `clear_router_decision_cache` was **not dead
  at all**: `decide_route` is memoized for 30 minutes on a key of question and
  hints only, its result reads two admin-editable settings (`ENABLE_CALIBRATION`
  through `_calibrated`, `ENABLE_WEB_ROUTE_DOWNGRADE` through `_llm_route`), and
  `apply_config_reload` did not clear it -- so toggling either from the console
  reported success and left every question already cached routing the old way
  until its entry expired. Same defect as the reranker's `lru_cache`, in a store
  `test_the_reload_reaches_every_cache_that_holds_an_editable_setting` cannot see,
  because that guard walks `@lru_cache` and this is hand-rolled. It is wired into
  the reload now.

  **`reachability.py` had a second bug of the first one's kind**, found by noticing
  it had never listed `_source_mtime_ns`. Its walk treated statements inside
  function bodies as module-level, so every name mentioned anywhere in a module
  became an import-time root -- and a helper called only from dead code looked
  alive. Fixed 2026-09-06; the correction surfaced six more, including
  `request_helpers.py::get_string_param` and `resilience.py::circuit_breaker_snapshot`,
  each called only from a function that is itself dead. Both of its bugs
  under- or over-reported in ways only reading caught, which is the argument for
  the docstring's "candidate, never a verdict" and for it never becoming a gate.

  **The third batch (2026-09-06) took 24 functions, five config classes and four
  "compatibility adapter" methods**, about 500 net lines. `api/utils/request_helpers.py`
  went entirely -- all four of its parameter helpers, and the module's only
  importer was `dependencies.py`'s `__getattr__` fallback list. The rest:
  `resilience.py` (four), `ingestion/processing/structure.py` (three),
  `evidence_conflict.py` (two, both labelled "legacy function kept for
  compatibility" with no compatibility to keep), `rag/web_utils.py` (three) and
  `agents/shared/config.py` (seven accessors).

  Three of those are worth knowing about beyond the line count:

  - **The circuit breaker is fine, and now has one implementation.**
    `call_with_circuit_breaker` is live in the reranker, the NLI stage and the
    graph client, and it inlines its own threshold-and-cooldown logic.
    `record_circuit_failure` / `record_circuit_success` were a second, unused
    implementation of the same thing over the same `_BREAKERS` registry -- two
    definitions of "record a failure", which is the divergence this file keeps
    recording, waiting to happen.
  - **`agents/shared/config.py`'s dead sections contradicted the running system.**
    `SynthesisConfig.enable_fact_verification` read `True` beside a synthesizer
    that passes `False`, and `RouterConfig.use_calibration` read `True` beside an
    `ENABLE_CALIBRATION` that defaults `False`. Anyone reading that file for the
    configuration found the opposite of what runs. `vector_rag` is the one section
    with a live reader (`app/agents/rag/vector.py`) and is what remains.
  - **`run_parallel_web_research` was a loaded gun.** It built a
    `ThreadPoolExecutor` over `run_web_research` -- precisely the shape that wedged
    this process at zero CPU through concurrent `DDGS()` construction (see Common
    Issues). It had never run. Its sibling `is_time_sensitive_query` was an
    English-only duplicate of the bilingual freshness pattern
    `KnowledgeAgentService` actually consults.

  **`cascade.py::_request` was a third kind of false positive**, and the reason the
  script says "confirm with `git grep -w`". It was reported TEST-ONLY because two
  test modules define their own local `_request` helper and the graph matches on
  name alone. In fact it had no test at all: its only consumers were
  `ValidationCascade.validate_level1` through `validate_level4`, four methods whose
  docstrings say they exist "for focused <stage>-stage tests" that do not exist --
  and which preserved the level numbering this file records as wrong
  (`validate_level2` called the NLI validator, `validate_level3` the citation one).
  Deleted with `run_cascade`, one more consumerless alias in the same class.

  **One thing was deliberately not deleted**, and it is the only entry left:
  `orchestration/engine.py::_terminal_payload`, unreachable because
  `OrchestrationEngine.execute_stream` is, and that because nothing calls
  `RAGPipeline.execute_stream`. That is a second streaming design on a declared
  Protocol, so removing it is a design decision rather than a cleanup -- written up
  as open technical debt under **SSE streaming** in Important Notes, which is where
  someone looking at streaming will actually land.

  **The fourth batch (2026-09-06) took the remaining 25 and three whole packages**,
  about 420 lines. The 25 were one-line-each confirmations -- every one had exactly
  one `git grep -w` hit, its own `def` -- and deleting them exposed one cascade,
  `registry.py::get_document_record`, whose only caller had been among them.

  The three packages are the more interesting half. `app/baselines/` was a
  re-export shim nothing imported, and it was the *only* importer of
  `app/evaluation/baselines/chroma/{vector,rerank,hybrid}.py` -- so those three
  died with it. **They are worth noticing on the way out**: each calls
  `self.vectorstore.similarity_search_with_relevance_scores(query, k=...)` on a raw
  Chroma handle, with no tenant, no owner and no source filter. That escapes
  `test_no_unrestricted_retrieval.py` entirely, because the guard looks for this
  repository's own `similarity_search` and these call LangChain's differently-named
  method on an injected store. Nothing constructed them, and the classes offer no
  way to scope a search, so wiring one up would have been an unscoped read across
  every tenant. The allowlisted harness is a different file --
  `baselines/api_retriever.py`, still live, still allowlisted, and
  `test_the_ownerless_allowlist_is_not_stale` still passes.

  `app/graph/streaming/` was the third, and it was already broken:
  `run_query_stream` imports `app.graph.streaming.stream_processor`, which does not
  exist, behind a function-local import -- the same defect shape as the
  `compatibility_post_execution` adapters in batch two, hidden the same way. Its own
  comment read "Retained import alias only; public API/SSE uses typed Engine
  streaming." The admin console's log-filter placeholder named
  `app.graph.streaming` as its example logger, in both locales; it names
  `app.orchestration.engine` now.

  **1 non-reachable definition remains in `app/`**, the deliberate one above: 0 in
  unimported modules, 0 reached only from tests. That is the clean ground for the
  85 `python:S3776` findings that are live code -- refactoring judgement now goes
  only to code that runs.
- **Answer provenance**: what a message may claim about where it came from is computed in
  one place — `retrieval_summary` (`app/api/routes/internal/pipeline_contract.py`), from the
  knowledge diagnostics both entry points already carry. **`used` means a source contributed
  evidence, not that it was selected**: a web search that returned nothing is not what a
  reader means by "this answer used the web". The response therefore keeps three states
  apart — `sources` (every source with its status, result count and reason), the derived
  `contributing_sources`, and `web_used` for older readers. There used to be only that
  boolean and **no endpoint set it**: the chat endpoint had no such key and the client
  defaulted a missing value to false, so every answer displayed `web: no`, including ones
  written entirely from web results. It is not only a badge —
  `score_memory_candidate` weights `web_used` at 0.20, so every long-term memory candidate
  had been scored as though the answer were purely local. A source that ran and found
  nothing is worth showing (it explains a thin answer); one skipped because the caller has
  no documents is not a fact about this answer, and the badge leaves it out.
- **Retry logic**: Retrieval retries retain their existing fallback policy; answer regeneration is capped at one retry per request
- **Circuit breaker**: Opens after 5 consecutive failures, closes after 60s cooldown
- **Stage timeouts and degradation** (reworked 2026-08-30): stage ceilings live in
  `Settings.stage_timeout_*` (read by `TimeoutConfig.from_settings`), not in a module
  constant. They bound a *hang*; they are not latency targets, which is why they sit well
  above the P95 target above — the previous hardcoded values (a 2s router covering up to
  three LLM calls, a 5s synthesis) fired on ordinary traffic. A tripped ceiling used to be
  an unconditional 500; now `_run_stage(..., on_timeout=…)` supplies what the run continues
  with, and the stage reports a `failed` event whose `failure_reason` reaches the caller
  through `execution_metadata.workflow_diagnostics`. **`privacy_permission` and
  `output_filter` deliberately have no `on_timeout`** — skipping scope resolution or output
  DLP is a hole, not a degradation — and they are listed in
  `timeout_control.MANDATORY_STAGES`, which exempts them from the total-budget gate so an
  exhausted budget upstream cannot squeeze the output filter out.
- **Caller deadlines** (wired 2026-08-31): `POST /api/advanced-rag/query` takes an optional
  `timeout_ms`, which becomes `PipelineRequest.deadline_at` and reaches
  `ExecutionBudget(config, deadline_at=…)`. It **narrows** `remaining_ms()` and never extends
  it, so a deadline beyond `STAGE_TIMEOUT_TOTAL_MS` does nothing and a caller cannot pin a
  worker by asking for an hour. The wire format is relative and the contract absolute on
  purpose: two clocks need not agree, but a budget consumed across stages must not be
  re-derived at each one. The offset is measured once and everything after it runs on
  `perf_counter`, so an NTP correction cannot move a live request's budget; a naive datetime
  is read as UTC. `MANDATORY_STAGES` still applies — an aggressive deadline is not a way to
  buy out of scope resolution or output DLP. Before this the field was accepted, forwarded
  through `PipelineRequest`, and read by nobody.

  The same wiring opens `request_context` around the workflow, which is what
  `app/services/runtime/request_context.py` exists for and what nothing on the request path
  had ever set. Three helpers check that deadline themselves: the synthesizer's self-review
  and fact-verification exits (both dormant), and `rule_rewrite._llm_rewrite`, which treats
  `remaining_seconds() is None` as "no time left" — so `QUERY_REWRITE_WITH_LLM` was a switch
  that could not turn anything on.
- **Verifier retry affordability**: a retry replays knowledge + synthesis + verification
  (`TimeoutConfig.retry_round_ms`). The verifier now downgrades `retry_retrieval` to
  `degraded` when the remaining budget cannot fund all three, instead of starting a round
  that the total-budget check kills — which turned a merely degraded answer into a failed
  request.
- **`ExecutionBudget.check_budget` had never fired** (fixed 2026-08-30): it tested
  `has_budget()`, whose `required_ms=0` default reduces it to `remaining_ms() >= 0`, and
  `remaining_ms` already clamps at 0. Exhaustion still surfaced, but as the next stage being
  clamped to a 0ms ceiling and cancelled — which reads in a trace as "that stage was slow"
  rather than "the request ran out of time".
- **Concurrent `DDGS()` construction wedges the process, and one query does it.** The web
  retriever builds a `primp.Client` (Rust) that calls back into Python logging on the way
  up; two workers doing that at once parked in `ddgs/http_client.py::__init__` at
  `logging.getLogger` while the main thread stuck in `Thread.start()`, and the server
  answered nothing — `/health` included — at zero CPU. `app/tools/web/search.py` holds
  construction under one lock and searches outside it. The cause is inside a third-party
  Rust client, so this contains the symptom rather than pretending to fix it there.
- **A stage failure reaches the API wrapped, twice.** `run_with_timeout` re-raises as
  `StageExecutionError` with the original on `__cause__`, and LangGraph may wrap that again,
  so `except SomeSpecificError` at an endpoint never fires — the first attempt at the fix
  below did exactly that and still returned 500.
  `app/api/routes/public/query.py::_retrieval_failure` walks the cause chain instead.
- **Every retrieval source failing is a 503, not a 500** (fixed 2026-09-02). With an empty
  corpus `vector` and `bm25` are *skipped*, so `web` is the only source that runs; when
  DuckDuckGo throttled, half the queries returned `500 "Unable to process advanced query"`,
  naming neither cause nor remedy. 500 says look at this service, 503 says look at what it
  depends on, and only one of those was true. The sibling case — sources never attempted,
  which must return quietly — was fixed earlier in `RAGAgentService.retrieve`.
- **Lazy imports on the request path are a deadlock risk, not a startup optimization**
  (found 2026-09-02 by running one query). `from ddgs import DDGS` does not import ddgs:
  the name is a proxy whose metaclass runs `importlib.import_module` on the first *call*,
  holding its own lock, and the module it imports calls `logging.getLogger` on the way in.
  One query starts several web searches on separate worker threads, so those are several
  concurrent first calls — three threads inside `_load_real`, one parked in
  `logging.getLogger`. **It wedged the whole process, not just the request**: the stuck
  thread holds the logging lock, so uvicorn's per-request access log blocks and `/health`
  stops answering while the event loop sits idle and healthy. The tell is a hang at zero
  CPU. `app/tools/web/search.py::_resolve_ddgs_eagerly` resolves it at import, when one
  thread is running; `tests/services/test_web_search_import.py` asserts no first-call
  import remains. The call site's `timeout=10` never applied — it bounds the HTTP request,
  not the import.
- **LLM request timeout**: `Settings.llm_request_timeout_seconds` is passed to the OpenAI and
  Anthropic chat clients. Without it a hung provider connection pinned a pool thread for the
  life of the process: an `asyncio` stage timeout unblocks the event loop but cannot cancel
  the thread inside a blocking `invoke()`. `ChatOllama` takes no equivalent parameter and is
  still uncapped.
- **Per-source vs per-stage timeouts**: `RAGAgentService`'s per-source bound derives from
  `KNOWLEDGE_SOURCE_TIMEOUT_MS` so it stays under `STAGE_TIMEOUT_RETRIEVAL_MS`. It used to be
  a hardcoded 30s under a 10s stage ceiling, so the inner bound could never fire.
- **Admin ops benchmark/replay corpus** (fixed 2026-08-30): `POST /admin/ops/benchmark/run` and
  `POST /admin/ops/replay/run` run their queries under the requesting admin's identity. They used to
  pass no actor at all, and every query died in the pipeline's first node — `privacy_permission`
  resolves an access scope and fails closed with "authenticated user identity is required". The
  consequence of the fix is that a run measures the corpus that admin can see (the shared
  `data/docs/` set plus their own and public documents) rather than a fixed corpus, so trends from
  two admins with different visible documents are not directly comparable. Scoping the runs to
  `data/docs/` instead was rejected: it would measure something no real query ever does, and would
  need a synthetic actor, reopening the fail-closed hole the resolver exists to close.
- **Benchmark query set** (2026-08-30): `run_benchmark` reads `data/eval/benchmark_queries.txt` if
  present, otherwise the tracked default `config/eval/benchmark_queries.txt`. It previously read only
  the `data/` path, which is gitignored runtime state — absent on every checkout where nobody placed
  it by hand, so the job died with "benchmark query set is empty" inside the background queue, where
  the endpoint's 202 response never surfaces it. `#` starts a comment in that file. The shipped set is
  a corpus-agnostic starter: it exercises pipeline latency and route branches, but grounding and
  citation numbers only mean something once the queries match documents actually in the corpus.
- **Session management**: Frontend supports session rename and pin features (added 2026-08-16). See `docs/development/daily-logs/2026-08-16/` for implementation details.
- **Clarification does not decide retrieval** (2026-08-30): missing fields ride on
  `RouteDecision.clarification_fields`, not on a substitute `route="clarification"`.
  The router used to return early with that route *before the LLM router ran*, and
  its `allowed_capabilities={"rag"}` removed graph and web from every
  comparison-shaped question -- which mattered most where it was least visible,
  since interactive clarification cannot happen inside the pipeline and the run
  continued with the original question on a route nothing had chosen for it.
- **Clarification System** (added 2026-08-17, revised 2026-08-29): Dynamic clarification based on intent complexity, capped by `max_rounds_for(intent)` — one round per field the question catalogue actually has a question for, so `rag_design`: 4, `document_comparison`: 1, and anything already complete or unrecognised: 0. (This bullet used to quote the hand-written table those numbers replaced on 2026-08-29 — 7 and 5 — which promised rounds that could not happen; see "Dormant by design" above.) Key service: `app/agents/clarification/service.py` and `rules.py`, reached through the resumable `/api/v1/clarification/check` HTTP endpoint (`app/api/routes/public/clarification.py`). Questions exist in Chinese and English (`_QUESTIONS_ZH` / `_QUESTIONS_EN`), selected from `force_language` or the query's script.

  **There was also a LangGraph `clarification` node, and it was removed on 2026-09-04.**
  It spent a `route_timeout_ms` ceiling and one clarifier call per incomplete question to
  produce two state values (`clarification`, `complete_query`) that nothing in `app/` read.
  It could not have done otherwise: the multi-round state lives in the session store behind
  the HTTP endpoint, so a graph node has no collected context to pass and the clarifier
  therefore always returned `action="ask"` — which the node logged and ignored, continuing
  with the original question. Feeding it that store from a graph node would have created a
  second, quieter definition of a clarification round, which is the failure this file
  already describes for the round counter. `RouteDecision.clarification_fields` still
  carries what is missing and `RouterDecision.completeness` still reports it;
  `tests/orchestration/test_clarification_is_not_a_pipeline_stage.py` guards that the
  deletion removed the no-op and not the feature. `EventStage` and the frontend's
  `EXECUTION_STAGES` lost the entry together, since an unknown stage makes the UI drop the
  event silently.
- **State management**: Frontend uses Zustand for global state, not Redux or Context API

## Common Issues

**"ModuleNotFoundError"**: Verify conda environment is activated
**"Neo4j connection failed"**: Neo4j is optional; system falls back to vector-only retrieval.
To actually start it locally, `make up` (and `make down` to stop it). That command
was broken until 2026-09-04 -- it ran `docker compose up -d neo4j` with no `-f`,
and there is no compose file in the repository root, so it only ever printed "no
configuration file provided". It now names deploy/compose/compose.yaml plus the
dev overlay, supplies `.runtime/development.env` (compose.yaml declares
NEO4J_PASSWORD with `:?`, so rendering fails without it), and deliberately passes
no `--project-directory`: the relative paths in those files are written for
deploy/compose/ as the base, and overriding it sends `env_file: ../../.runtime/...`
and the `../../app` bind mounts two levels too high.

**The graph ports are published in development only.** compose.yaml maps nothing
-- containers reach each other over the `querymind` network and the backend uses
`bolt://neo4j:7687` -- but a locally run `uvicorn` is not on that network, and
`NEO4J_URI` defaults to `bolt://localhost:7687`. So compose.dev.yaml publishes
7474 (Browser) and 7687 (Bolt) on `127.0.0.1`, like every other port in that
file: this Neo4j holds a password from `.runtime/`, and `0.0.0.0` would offer it
to the local network. `tests/core/test_dev_compose_is_usable.py` pins both halves
-- the ports exist in development, and they still do not exist in production.

That suite carried a defect of exactly the kind this file keeps recording, found
2026-09-05 by running the suite in a fresh worktree. It read the `-f` arguments
with `re.findall(r"-f (\S+)", recipe)` over the **whole** recipe, and the recipe's
first line is a shell guard, `@test -f .runtime/development.env || ...`, whose
`-f` is test(1)'s file predicate. So the test asserted that a **gitignored**
runtime file exists: green on a machine that has run `make config-render`, red on
every fresh clone and in CI, which renders nothing before `pytest`. The match is
scoped to the `docker compose` line now, and
`test_make_up_only_names_files_that_ship` asserts each one is tracked by git --
which is what the broken assertion was accidentally reaching for.

Note what you will see once it is up: with `MODEL_BACKEND=local` the graph is
**empty by design**, because rule-extracted triplets are now correctly filtered
out (see "Knowledge graph extraction"). An empty Neo4j Browser there is the
system working, not a broken ingest.
**Frontend CORS errors**: Ensure backend is running on port 8000

## Documentation Management

### Daily Work Logs

All daily work should be documented in `docs/development/daily-logs/YYYY-MM-DD/` (create the
folder and files manually — `scripts/create_daily_log.py` was removed ahead of the v0.7 rewrite).

Each day should include:
- `plan.md` - Daily goals and tasks
- `implementation.md` - Code changes and technical details
- `decisions.md` - Technical decisions and rationale
- `summary.md` - Completion status and lessons learned

**Important**: Keep project clean by moving any temporary documentation created elsewhere in the repo into the corresponding date folder at end of day. See [docs/development/daily-logs/README.md](docs/development/daily-logs/README.md) for detailed guidelines.
