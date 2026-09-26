# Lenovo Leap: Current Problems and Build Checklist

Project: AI in Education and Skill Learning

This document tracks the current defects, incomplete workflows, and improvement work identified during repository review. Items are ordered by implementation dependency and demo risk. The Gemini model switch is treated as intentional; provider-specific concerns are listed separately from the core workflow defects.

## Preserved Implementation Status

The completed fixes from Phases 1–3 remain part of this checklist and should not be regressed. Current Phase 4 progress:

- [x] Tutor history is persisted and restored in the tutor UI.
- [x] Tutor responses expose grounded resources and support language selection.
- [x] Learning-plan and tutor resources open through safe external links when a URL is available.
- [x] Onboarding choices preserve the original broad pathways: Data Analyst, Data Scientist, Software Engineer, AI Engineer, Cybersecurity Engineer, Product Manager, and Entrepreneur.
- [x] Benchmark profiles map the restored pathways to grounded Python, SQL, statistics, and visualization curriculum/resources.
- [x] Unsupported career paths are rejected instead of silently falling back to Data Analyst.
- [x] Progress compares readiness across persisted assessment attempts, and the learning plan exposes a targeted reassessment entry point.
- [x] Phase 6 includes health endpoints, bounded external-service retries, offline backend contract tests, setup documentation, and environment examples.
- [ ] Add broader non-data career packages or explicitly keep them out of onboarding until curriculum, benchmarks, questions, and resources exist.

## Priority 0: Runtime and Workflow Blockers

### P0-00: Add structured, colorized workflow logging

**Problem:** Scattered `print()` calls make it difficult to trace one learner through IRT, BKT, DAG traversal, RAG, and LLM execution.

**Files to create:**

- `server/core/logger.py`

**Files to modify:**

- `server/agent/nodes/assessment.py`
- `server/services/ml_engine.py`
- `server/services/knowledge_graph.py`
- `server/services/rag_service.py`
- `server/agent/nodes/gap_career.py`
- `server/agent/nodes/content_tutor.py`
- `server/agent/nodes/planning.py`

**Required trace events:** `[IRT]` answer/correctness/theta/difficulty, `[BKT]` concept/mastery, `[DAG]` direction/next concept, `[RAG]` query/count/top score, and `[LLM]` model/duration/fallback/schema status.

**Constraint:** Use logging levels and environment-controlled ANSI colors. Never log passwords, tokens, full learner messages, or sensitive prompt contents.

---

### P0-01: Correct assessment graph sequencing and normalize payloads

**Problem:** Answer submission can run `assessment_node` before `record_answer_node`, replacing the active question before grading it. Start and submit responses also use different question keys.

**Expected behavior:** Start generates question 1; submit evaluates the current answer exactly once, then generates the next question or runs remediation. Both endpoints return `session_id`, `question`, `current_step`, `total_steps: 8`, and `is_assessment_complete`.

**Files to modify:**

- `server/agent/graph.py`
- `server/agent/nodes/assessment.py`
- `server/routers/navigator.py`
- `client/src/pages/Assessment.jsx`

**Tests to modify or create:**

- `server/scripts/tests/test_graph.py`
- `server/scripts/tests/test_security_contract.py`
- Create an API-level assessment flow test.

**Thread ID constraint:** A fixed `user_{user_id}_assessment` thread supports one lifetime attempt only. For assessment history and retakes, use a unique attempt/thread ID and persist its association in `AssessmentSession`.

---

### P0-02: Migrate structured LLM outputs to typed schemas

**Problem:** Nodes manually prompt for JSON and parse it with cleanup, `json.loads()`, or `ast.literal_eval()`.

**Files to create:**

- `server/schemas/agent_outputs.py`

**Schemas:** `GeneratedQuestionSchema`, `GapAnalysisSchema`, and `StudyPlanSchema`. Tutor markdown should remain text; only wrap it in a schema if metadata is also required.

**Files to modify:**

- `server/agent/nodes/assessment.py`
- `server/agent/nodes/gap_career.py`
- `server/agent/nodes/planning.py`
- `server/agent/nodes/content_tutor.py`

**Expected behavior:** Use `llm.with_structured_output(SchemaClass)` for structured calls, validate bounds and required fields, and retain deterministic fallbacks. Confirm the selected Gemini model and installed integration support structured output before removing compatibility paths.

---

### P0-03: Assessment sessions cannot reliably resume after refresh

**Problem:** The assessment page starts with empty local state and does not restore an active session.

**Files to modify:**

- `client/src/pages/Assessment.jsx`
- `client/src/services/api.js`
- `server/routers/navigator.py` if a dedicated resume endpoint is needed

**Expected behavior:** On page load, restore the active assessment and display its current question without creating a duplicate attempt.

---

### P0-04: Fix SQLAlchemy relationship configuration

**Problem:** `AssessmentSession.user` references `back_populates="assessment_sessions"`, so `User` must define the matching relationship.

**Files to modify:**

- `server/models/user.py`
- `server/models/assessment.py` if alignment is needed

**Verification:** Import all models and query assessment history in a clean server process.

---

### P0-05: Make runtime setup reproducible

**Problem:** PostgreSQL, LangGraph checkpointing, Gemini, Pinecone, and optional NVIDIA setup is not documented as one reproducible workflow.

**Files to modify or create:**

- `README.md`
- `client/README.md`
- `server/requirements.txt` if imports and declarations differ
- Create `server/.env.example` if absent

**Expected behavior:** A new developer can configure services, migrate, seed vectors, start both services, and run tests without guessing.

---

## Priority 1: Personalization and Data Integrity

### P1-01: Map onboarding profile completely and fix time-budget math

**Problem:** `_profile_state()` does not pass every relevant onboarding field, especially `preferred_question_types` and `secondary_language`. Weekly hours are also treated as daily minutes.

**Files to modify:**

- `server/routers/navigator.py`
- `server/agent/state.py` if normalization needs explicit fields

**Expected behavior:** Map language, level, career, question types, and weekly commitment. Calculate `daily_time_minutes = (time_commitment_hrs * 60) / 7` with an explicit rounding policy, while preserving direct API daily-minute overrides.

---

### P1-02: Normalize answer options before grading

**Problem:** Grading compares strings or their first two characters, which is fragile for letter choices, prefixes, whitespace, and generated answers.

**Files to modify:**

- `server/agent/nodes/assessment.py`

**Files to create if needed:**

- `server/services/answer_evaluator.py`

**Expected behavior:** Map `A`/`B`/`C`/`D` to the corresponding option, strip prefixes such as `A) ` and `a. `, normalize whitespace/case, and define a safe explicit policy for actual coding answers. Never execute arbitrary learner code in the API process.

---

### P1-03: Validate all LLM outputs before state updates

**Problem:** Malformed or incomplete Gemini output can enter graph state.

**Files to modify:**

- `server/agent/nodes/assessment.py`
- `server/agent/nodes/gap_career.py`
- `server/agent/nodes/planning.py`
- `server/agent/nodes/content_tutor.py`
- `server/schemas/agent_outputs.py`

**Expected behavior:** Enforce numeric bounds, required fields, question options, gap structure, seven-day plan structure, and resource references. Invalid output must use a deterministic fallback.

## Priority 2: Persistence, API, and Debugging

### P2-01: Persist tutor chat history to the LangGraph checkpoint

**Problem:** `/navigator/tutor/chat` returns new turns but does not save them, so later requests may not see prior conversation.

**Files to modify:**

- `server/routers/navigator.py`
- `server/agent/graph.py` or `server/services/checkpoint_store.py` if a checkpoint update helper is needed

**Expected behavior:** Persist bounded history to the authenticated assessment thread using the official saver API, with clear behavior when no assessment session exists.

---

### P2-02: Define the tutor empty-state contract

**Problem:** A learner with onboarding but no assessment may receive a not-found error from the tutor endpoint.

**Files to modify:**

- `server/routers/navigator.py`
- `client/src/pages/Tutor.jsx`

**Expected behavior:** Either require an assessment and guide the learner to start one, or support a profile-based tutor context.

---

### P2-03: Do not render raw gap objects in React

**Problem:** `priority_gaps` contains dictionaries, but React cannot render a plain object directly.

**Files to modify:**

- `client/src/pages/Dashboard.jsx`

**Expected behavior:** Render `career_skill`, `severity`, `required_benchmark`, `current_score`, `gap_size`, and `root_cause_concept` as structured fields.

---

### P2-04: Expose ML debug payload only in development

**Problem:** Internal theta, mastery, and domain scores are useful for Network Tab debugging but should not be exposed unconditionally.

**Files to modify:**

- `server/routers/navigator.py`
- `server/core/config.py`

**Expected behavior:** Add `_debug: {theta, concept_mastery, domain_scores}` only when an explicit development/debug setting is enabled. Never expose it in production responses.

---

### P2-05: Persist study-plan completion

**Problem:** Plan items have `completion_status`, but no API or database model stores progress.

**Files to modify or create:**

- `server/models/assessment.py` or a dedicated learning-plan model
- `server/schemas/navigator.py`
- `server/routers/navigator.py`
- `server/agent/state.py`
- `client/src/pages/LearningPlan.jsx`
- `client/src/services/api.js`
- Create an Alembic migration for persisted plan progress.

---

### P2-06: Add assessment result detail and history association

**Problem:** History lists sessions but does not expose responses, gaps, plan, or tutor output for a selected attempt.

**Files to modify:**

- `server/routers/navigator.py`
- `client/src/pages/History.jsx`
- `client/src/services/api.js`

**Files to create:**

- `client/src/pages/AssessmentResult.jsx`

---

### P2-07: Checkpoint and assessment-session state can diverge

**Problem:** Session metadata is updated separately from LangGraph state. Failures between graph persistence and SQL commit can leave status, question count, or readiness score inconsistent.

**Files to modify:**

- `server/routers/navigator.py`
- `server/services/checkpoint_store.py`

**Expected behavior:** Define failure recovery and idempotency rules for start, submit, complete, and analyze-and-plan operations.

---

## Priority 3: Frontend Data and UX Defects

### P3-01: Dashboard does not present complete gap intelligence

**Problem:** After the P2 crash fix, the dashboard still needs a useful presentation of gap severity, prerequisite path, benchmark, current mastery, and recommended next action rather than a minimal text list.

**Files to modify:**

- `client/src/pages/Dashboard.jsx`

**Expected behavior:** Present prioritized gaps with career skill, severity, current score, required benchmark, gap size, root cause, prerequisite path, and a link into the learning plan or tutor.

---

### P3-02: Learning plan page ignores the actual plan schema

**Problem:** Backend plan items contain `day`, `focus_topic`, `duration_minutes`, `learning_objectives`, `activities`, and `recommended_resources`. The frontend mostly checks `title`, `topic`, or `description`.

**Files to modify:**

- `client/src/pages/LearningPlan.jsx`
- `client/src/pages/Dashboard.jsx`

**Expected behavior:** Display the complete seven-day plan with activities, time budgets, objectives, and resources.

---

### P3-03: Assessment results are not shown to the learner

**Problem:** Completion only shows a generic completion message. Readiness score, domain scores, mastery, gaps, and localized explanation are not presented in the assessment flow.

**Files to modify:**

- `client/src/pages/Assessment.jsx`
- `client/src/pages/Dashboard.jsx`
- `client/src/pages/Progress.jsx`

**Expected behavior:** Provide a clear completion state with meaningful results and links to the plan and tutor.

---

### P3-04: Progress page is too narrow for the available analytics

**Problem:** It displays concept mastery but not domain scores, readiness trend, gap severity, or comparison with prior attempts.

**Files to modify:**

- `client/src/pages/Progress.jsx`
- `client/src/services/api.js`
- `server/routers/navigator.py` if additional aggregate data is needed

---

### P3-05: Tutor UI does not expose language selection or grounded context

**Problem:** The backend supports language-specific tutoring and grounded resources, but the UI does not let the learner choose language or see the resources used.

**Files to modify:**

- `client/src/pages/Tutor.jsx`
- `client/src/services/api.js`

---

### P3-06: Loading, retry, and error handling are inconsistent

**Problem:** Several pages use compressed one-line components, generic errors, fixed response time, and limited retry/resume behavior. AI calls may take longer than ordinary API calls.

**Files to modify:**

- `client/src/pages/Assessment.jsx`
- `client/src/pages/Tutor.jsx`
- `client/src/pages/LearningPlan.jsx`
- `client/src/pages/Progress.jsx`
- `client/src/pages/History.jsx`
- `client/src/services/api.js`

---

### P3-07: Assessment response time is hard-coded

**Problem:** The client submits `response_time_sec: 20` for every answer, so struggle-risk analytics do not reflect actual learner behavior.

**Files to modify:**

- `client/src/pages/Assessment.jsx`

**Expected behavior:** Measure time from question display to answer submission, pause safely when the page is hidden, and send the measured value.

---

## Priority 4: Learning Product Completeness

### P4-01: No re-assessment loop after remediation

**Problem:** The plan promises skill improvement, but there is no explicit way to retake targeted questions and measure improvement.

**Files to modify:**

- `server/agent/graph.py`
- `server/agent/nodes/assessment.py`
- `server/routers/navigator.py`
- `client/src/pages/LearningPlan.jsx`
- `client/src/pages/Progress.jsx`

---

### P4-02: No progress comparison across assessment attempts

**Problem:** History stores readiness scores, but the UI does not compare domain or concept progress across attempts.

**Files to modify:**

- `server/routers/navigator.py`
- `client/src/pages/History.jsx`
- `client/src/pages/Progress.jsx`

---

### P4-03: Coding assessment questions are not truly coding assessments

**Problem:** Curriculum entries label some questions as `Coding`, but they are still multiple-choice questions. There is no safe code editor, test case runner, or code-specific evaluation.

**Files to modify or create:**

- `server/data/curriculum.json`
- `server/agent/nodes/assessment.py`
- Create a sandboxed code evaluation service only after defining strict security limits.
- `client/src/pages/Assessment.jsx`

**Current status:** Deliberately not enabled. Coding-labelled items remain safe multiple-choice diagnostics; arbitrary learner code is not executed in the API process. A separate sandbox service with strict resource, filesystem, network, and process limits is required before this item can be marked complete.

---

### P4-04: Subject and career support is narrower than onboarding implies

**Problem:** Onboarding offers multiple subjects and careers, but curriculum and career benchmarks are primarily Data Analytics/Data Analyst oriented. Other selections may silently fall back to SQL/Data Analyst.

**Files to modify:**

- `server/data/curriculum.json`
- `server/data/career_benchmarks.json`
- `server/services/knowledge_graph.py`
- `server/services/career_benchmarks.py`
- `server/agent/nodes/assessment.py`
- `client/src/pages/Onboarding.jsx`

**Expected behavior:** Either constrain onboarding to supported pathways or add curriculum and benchmark coverage for each advertised pathway.

---

### P4-05: Resource grounding is optional but not clearly surfaced

**Problem:** Local concept lookup works without Pinecone, but vector search silently returns empty results if credentials or indexing are unavailable. The learner cannot tell whether recommendations are grounded.

**Files to modify:**

- `server/services/rag_service.py`
- `server/agent/nodes/content_tutor.py`
- `client/src/pages/Tutor.jsx`
- `client/src/pages/LearningPlan.jsx`

**Expected behavior:** Expose resource provenance and distinguish local fallback content from vector-grounded recommendations.

---

## Priority 5: Security, Reliability, and Maintainability

### P5-01: JWT is stored in localStorage

**Problem:** A client-side XSS issue could expose the access token.

**Files to modify:**

- `server/routers/auth.py`
- `server/core/security.py`
- `client/src/context/AuthContext.jsx`
- `client/src/services/api.js`

**Potential solution:** Use secure httpOnly cookies with CSRF protection, or document and mitigate the current bearer-token design for the hackathon.

**Current status:** Documented as a production hardening requirement; the current hackathon bearer-token contract remains unchanged.

---

### P5-02: CORS and deployment configuration need production boundaries

**Problem:** Configuration is improved from the original wildcard setup, but deployment-specific origins and proxy behavior need explicit validation.

**Files to modify:**

- `server/core/config.py`
- `server/main.py`
- `docker-compose.yml`
- `.env.example` or `server/.env.example`

---

### P5-03: External AI and vector service calls lack shared retry/observability policy

**Problem:** Nodes catch exceptions and print messages, but there is no structured logging, retry policy, correlation ID, or service health status.

**Files to modify:**

- `server/agent/nodes/assessment.py`
- `server/agent/nodes/gap_career.py`
- `server/agent/nodes/content_tutor.py`
- `server/agent/nodes/planning.py`
- `server/services/rag_service.py`

**Files to create:**

- Create a shared logging/configuration utility if needed.
- Add health endpoints for database, checkpointing, and optional AI services.

---

### P5-04: Automated test organization is incomplete

**Problem:** Tests live under `server/scripts/tests`, `pytest` configuration is absent, and some tests require live Pinecone credentials. There is no frontend or browser-level test suite.

**Files to modify or create:**

- Move or duplicate tests into `server/tests/`.
- Create `server/pytest.ini` or configure testing in `pyproject.toml`.
- Create fixtures for database and checkpoint isolation.
- Create client tests or Playwright tests.
- Separate offline deterministic tests from live integration tests.

**Current status:** Added `server/tests`, `server/pytest.ini`, and offline service contract tests. Full database/checkpoint/API/browser coverage remains a follow-up.

**Minimum test coverage:**

- Auth and onboarding API flow.
- Assessment start, answer, resume, and completion flow.
- Server-side answer privacy contract.
- Checkpoint persistence.
- Dashboard/history API responses.
- Tutor history persistence.
- Frontend assessment flow with real response shapes.

---

### P5-05: Product naming is inconsistent

**Problem:** The repository uses `Learning Navigator` and `PathForge` in different user-facing and agent-facing locations.

**Files to modify:**

- `client/src/components/Navbar.jsx`
- `client/src/components/AppShell.jsx`
- `client/src/pages/Landing.jsx`
- `server/agent/prompts.py`
- `server/main.py`
- `README.md`

**Expected behavior:** Select one product name and use it consistently in UI, prompts, API metadata, and documentation.

---

## Recommended Fix Order

### Phase 1: Core System Observability and Critical Runtime Blockers

1. **P0-00**: Add structured, colorized console logging.
2. **P0-04**: Fix SQLAlchemy relationship configuration on the `User` model.
3. **P0-01**: Correct assessment graph sequencing and normalize response payloads.
4. **P2-07**: Define failure recovery and idempotency rules to prevent divergence between PostgreSQL checkpoints and assessment sessions.
5. **P0-03**: Add active assessment session resume behavior on page load and refresh.

### Phase 2: Personalization, Data Integrity, and Typed Schemas

1. **P1-01**: Map all onboarding fields and fix weekly-to-daily time conversion.
2. **P1-02**: Normalize student answer choices before grading.
3. **P3-07**: Calculate actual question response time in the frontend.
4. **P0-02 and P1-03**: Migrate to typed Pydantic schemas and validate LLM outputs before state updates.

### Phase 3: Persistence, Debugging, and State Flow Fixes

1. **P2-01**: Persist tutor chat history to the PostgreSQL LangGraph checkpoint.
2. **P2-02**: Define the tutor empty-state contract for learners without an assessment.
3. **P2-03 and P3-01**: Fix React gap rendering and present gap intelligence properly.
4. **P3-02**: Align the Learning Plan UI with the backend plan schema.
5. **P2-04**: Add a development-only `_debug` ML payload.
6. **P2-05**: Implement learning-plan activity completion tracking and API persistence.
7. **P2-06**: Add the assessment result detail endpoint and history association.

### Phase 4: Frontend UX, Analytics, and Grounding

1. **P3-03**: Render complete assessment results and score breakdowns after the eighth question.
2. **P3-04**: Expand Progress with domain scores, readiness trends, and gap severity.
3. **P3-05**: Add language selection and grounded resource visibility to the Tutor UI.
4. **P3-06**: Standardize loading states, retries, and error boundaries across AI pages.
5. **P4-05**: Surface Pinecone versus fallback resource grounding clearly to learners.

### Phase 5: Extended Product Features and Re-assessment

1. **P4-01**: Add the re-assessment loop after study-plan completion.
2. **P4-02**: Add progress comparison across assessment attempts.
3. **P4-03**: Implement safe, sandboxed coding-question evaluation.
4. **P4-04**: Align onboarding subject and career choices with actual benchmark and curriculum coverage.

### Phase 6: Deployment, Testing, Security, and Hardening

1. **P5-04**: Establish automated integration tests, checkpoint isolation, and API-flow coverage.
2. **P5-01**: Harden authentication security, including evaluating httpOnly cookies versus localStorage.
3. **P5-02**: Validate CORS and deployment proxy boundaries.
4. **P5-03**: Implement shared retry policies and health endpoints for external AI services.
5. **P0-05**: Document reproducible runtime setup, environment variables, migrations, and vector seeding.
6. **P5-05**: Unify product naming across the codebase.

## Definition of Done for the Hackathon Demo

- A new user can register, complete onboarding, start an assessment, answer every question, and see each next question.
- Refreshing the assessment page resumes the same active attempt.
- The final assessment produces readiness, domain scores, gaps, grounded explanation, and a seven-day plan.
- Dashboard, progress, history, learning plan, and tutor pages render the actual backend response structures without React errors.
- Tutor conversation persists for the active learner context.
- The complete flow works with Gemini configured and still has a deterministic fallback when AI services are unavailable.
- A documented setup command sequence and repeatable tests verify the demo path.