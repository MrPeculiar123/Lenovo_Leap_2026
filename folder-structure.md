# AI-Powered Personal Learning & Career Navigator

## Architecture, File Implementation Order & Repository Blueprint

This document outlines the final repository structure, the complete list of files to be created and modified, and the exact step-by-step implementation order for the **AI in Education and Skilling (Personal Learning & Career Navigator)** system.

---

## 1. Streamlined Architecture Summary

To maximize efficiency and minimize latency for a real-time interactive demo, the multi-agent system consolidates tightly coupled LLM tasks from 6 separate hops into **3 primary LLM Agent nodes** supported by a deterministic **ML Service Tool** and **Planning Agent**:

```
[ 1. Student Onboarding ] (Domain, Target Career, Regional Language, Daily Time)
           │
           ▼
[ 2. Adaptive Assessment Agent ] (CAT / IRT Dynamic Questions across Prerequisite Graph)
           │
           ▼
[ 3. ML Service Tool (pyBKT) ] ──► (Deterministic: Computes Latent Concept Mastery Probabilities)
           │
           ▼
[ 4. Gap Analysis & Career Agent ] ──► (Combined: Career Benchmarks + Root-Cause Prerequisite DAG)
           │
           ▼
[ 5. Content & Regional Tutor Agent ] ──► (Combined: Vector RAG Search + Code-Switched Explanations)
           │
           ▼
[ 6. Planning Agent ] ──► (Builds Daily Time-Boxed 7-Day Roadmap)
           │
           ▼
[ 7. Continuous Reassessment Loop ] ──► (Student Practice Updates ML Profile)
```

---

## 2. Final Repository Directory Structure

```
Lenovo_Leap_2026/
├── docker-compose.yml
├── README.md
├── folder-structure.md                  # This architecture blueprint
├── .env
│
├── server/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                          # Registers auth, onboarding, and navigator routers
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── core/
│   │   ├── config.py                    # App settings, DB URL & LLM API keys
│   │   ├── database.py                  # SQLAlchemy engine & session maker
│   │   └── security.py                  # Password hashing & JWT tokens
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                      # User & UserProfile SQLAlchemy models
│   │   └── learning.py                  # Assessment, Mastery & StudyPlan models [NEW]
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                      # Auth request/response schemas
│   │   ├── onboarding.py                # Onboarding profile schemas
│   │   └── navigator.py                 # Assessment, Plan & Tutor schemas [NEW]
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                      # /api/auth endpoints
│   │   ├── onboarding.py                # /api/onboarding endpoints
│   │   └── navigator.py                 # /api/navigator endpoints [NEW]
│   ├── services/                        # Deterministic tools & knowledge bases [NEW]
│   │   ├── knowledge_graph.py           # Prerequisite concept DAG & traversal [NEW]
│   │   ├── ml_engine.py                 # pyBKT mastery formulas & struggle scorer [NEW]
│   │   ├── career_benchmarks.py         # Career benchmark skill maps [NEW]
│   │   └── rag_service.py               # Vector search & grounded learning content [NEW]
│   └── agent/                           # LangGraph multi-agent workflow [NEW]
│       ├── __init__.py
│       ├── state.py                     # StudentState TypedDict schema [NEW]
│       ├── prompts.py                   # CAT, Gap/Career, Regional Tutor prompts [NEW]
│       ├── graph.py                     # Compiled LangGraph StateGraph [NEW]
│       └── nodes/
│           ├── __init__.py
│           ├── assessment.py            # Adaptive Assessment Agent node [NEW]
│           ├── gap_career.py            # Combined Gap Analysis & Career Agent node [NEW]
│           ├── content_tutor.py         # Combined Content & Regional Tutor node [NEW]
│           └── planning.py              # 7-Day Planning Agent node [NEW]
│
└── client/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx                      # App router with protected routes
        ├── index.css
        ├── context/
        │   └── AuthContext.jsx          # Auth & user state context
        ├── services/
        │   └── api.js                   # API client (Auth, Onboarding, Navigator)
        ├── components/
        │   ├── Button.jsx
        │   ├── Input.jsx
        │   ├── Navbar.jsx
        │   ├── Loading.jsx
        │   ├── ProtectedRoute.jsx
        │   ├── SkillBars.jsx            # Skill mastery vs benchmark bars [NEW]
        │   ├── GapAnalysisCard.jsx      # Root-cause prerequisite gap card [NEW]
        │   ├── RoadmapTimeline.jsx      # Interactive 7-day study plan [NEW]
        │   └── TutorChatDrawer.jsx      # Multilingual regional AI tutor chat [NEW]
        └── pages/
            ├── Landing.jsx              # Hero landing page
            ├── Login.jsx                # Login & Registration
            ├── Onboarding.jsx           # Multi-step preferences onboarding
            ├── Assessment.jsx           # Interactive adaptive quiz page [NEW]
            └── Dashboard.jsx            # Dynamic learning & career dashboard [REVAMPED]
```

---

## 3. Step-by-Step File Implementation Order

Implementation proceeds in a dependency-first, bottom-up order across 4 distinct phases:

### Phase 1: Core Foundation & Deterministic Tools

*Provides the mathematical and semantic foundation so agents have deterministic tools to call.*

| # | File Path                                | Action  | Description                                                                                                                                                                                                        |
| - | ---------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1 | `server/services/knowledge_graph.py`   | `NEW` | Directed Acyclic Graph (DAG) of prerequisite concepts (e.g., Set Theory&rarr; Relational Algebra &rarr; SQL Basics &rarr; Joins &rarr; Aggregations). Supports root-cause backward traversal when a concept fails. |
| 2 | `server/services/ml_engine.py`         | `NEW` | Bayesian Knowledge Tracing (BKT) engine calculating latent mastery probabilities$P(L_t)$ from answers, attempts, and latency. Includes IRT difficulty updates and struggle risk estimation.                      |
| 3 | `server/services/career_benchmarks.py` | `NEW` | Role benchmark skill profiles (e.g.,*Data Analyst*: SQL 75%, Python 70%, Data Viz 70%, Stats 60%; *Data Scientist*, *Backend Engineer*).                                                                     |
| 4 | `server/services/rag_service.py`       | `NEW` | Semantic retriever over educational materials (bite-sized notes, video timestamps, documentation, practice exercises) mapped to knowledge graph concepts.                                                          |

---

### Phase 2: LangGraph Multi-Agent Workflow

*Assembles the 3 combined LLM agent nodes + ML tool into the compiled StateGraph.*

| #  | File Path                               | Action  | Description                                                                                                                                                                                                                           |
| -- | --------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5  | `server/agent/state.py`               | `NEW` | `StudentState` TypedDict definition: tracks `student_id`, `subject`, `target_career`, `language`, `skill_scores`, `priority_gaps`, `grounded_resources`, `study_plan`, and `next_action`.                         |
| 6  | `server/agent/prompts.py`             | `NEW` | Optimized system prompts with strict JSON outputs for adaptive assessment (CAT/IRT), combined gap/career analysis, code-switched regional tutoring (Marathi/Hindi/English), and time-boxed planning.                                  |
| 7  | `server/agent/nodes/assessment.py`    | `NEW` | **Adaptive Assessment Agent Node**: selects/generates 6–8 dynamic diagnostic questions tailored to the student's perceived level across the prerequisite tree.                                                                 |
| 8  | `server/agent/nodes/gap_career.py`    | `NEW` | **Gap Analysis & Career Agent Node (Combined)**: executes career benchmark matching + root-cause knowledge graph traversal in one prompt step.                                                                                  |
| 9  | `server/agent/nodes/content_tutor.py` | `NEW` | **Content & Regional Tutor Agent Node (Combined)**: pulls RAG vector chunks for root-cause gaps and immediately generates code-switched regional explanations.                                                                  |
| 10 | `server/agent/nodes/planning.py`      | `NEW` | **Planning Agent Node**: creates an adaptive 7-day daily study roadmap matching the student's daily time limit (e.g., 60 mins/day).                                                                                             |
| 11 | `server/agent/graph.py`               | `NEW` | Compiles the LangGraph`StateGraph`, connecting: `Orchestrator` &rarr; `Assessment` &rarr; `ML Tool` &rarr; `Gap & Career` &rarr; `Content & Tutor` &rarr; `Planner` &rarr; Output, with conditional reassessment edges. |

---

### Phase 3: Database Models, Schemas & Backend API

*Persists the learning state and exposes endpoints for frontend consumption.*

| #  | File Path                       | Action     | Description                                                                                                                                                                                                       |
| -- | ------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 12 | `server/models/learning.py`   | `NEW`    | SQLAlchemy models:`AssessmentSession`, `QuestionResponse`, `ConceptMastery`, and `StudyPlan`.                                                                                                             |
| 13 | `server/schemas/navigator.py` | `NEW`    | Pydantic validation schemas:`StartAssessmentResponse`, `SubmitAnswerRequest`, `AnswerResultResponse`, `GeneratePlanResponse`, `TutorChatRequest`, `TutorChatResponse`, and `DashboardDataResponse`. |
| 14 | `server/core/config.py`       | `MODIFY` | Add LLM API keys and model configuration (e.g.,`GEMINI_API_KEY`, `LLM_MODEL`).                                                                                                                                |
| 15 | `server/routers/navigator.py` | `NEW`    | FastAPI endpoints for`/api/navigator/start-assessment`, `/api/navigator/submit-answer`, `/api/navigator/analyze-and-plan`, `/api/navigator/tutor/chat`, and `/api/navigator/dashboard-data`.            |
| 16 | `server/main.py`              | `MODIFY` | Register the`/api/navigator` router.                                                                                                                                                                            |

---

### Phase 4: Frontend Components & Client Integration

*Builds the interactive learning experience in React + Tailwind CSS.*

| #  | File Path                                     | Action     | Description                                                                                                                  |
| -- | --------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 17 | `client/src/services/api.js`                | `MODIFY` | Add API client helper methods for all`/api/navigator/*` endpoints.                                                         |
| 18 | `client/src/components/SkillBars.jsx`       | `NEW`    | Visual skill mastery progress bars comparing current student mastery vs career benchmark per concept.                        |
| 19 | `client/src/components/GapAnalysisCard.jsx` | `NEW`    | Visual card explaining root-cause prerequisite gaps (e.g., "SQL Joins gap traces back to Set Theory fundamentals").          |
| 20 | `client/src/components/RoadmapTimeline.jsx` | `NEW`    | Interactive 7-day schedule with time-boxed daily tasks, badges, and linked learning resources.                               |
| 21 | `client/src/components/TutorChatDrawer.jsx` | `NEW`    | Slide-out AI tutor chat with live language switching (Marathi, Hindi, English) and code-switched explanations.               |
| 22 | `client/src/pages/Assessment.jsx`           | `NEW`    | Dynamic assessment page: question cards, option selection, timer, instant feedback, and submission transition.               |
| 23 | `client/src/pages/Dashboard.jsx`            | `MODIFY` | Wire up live dashboard state: career readiness badge, skill mastery breakdown, prerequisite gaps, 7-day plan, and tutor CTA. |
| 24 | `client/src/App.jsx`                        | `MODIFY` | Register the`/assessment` route under `ProtectedRoute`.                                                                  |

---

## 4. Key Demo Verification Scenario (Slide 14 Persona)

- **Student Profile**: Career = *Data Analyst*, Language = *Marathi*, Time Commitment = *1 hr/day*.
- **Assessment Results**: Python: 82%, SQL: 43%, Data Visualization: 35%, Statistics: 61%.
- **Gap & Career Outcome**: SQL & Visualization flagged as blocking gaps; SQL gap is traced to missing Set Theory / Join prerequisites.
- **Content & Regional Tutor Outcome**: Explains concepts in Marathi with technical English terms retained, grounded in retrieved RAG resources.
- **Planning Outcome**: 7-Day daily time-boxed roadmap targeting root-cause remediation first before advancing to complex queries.
