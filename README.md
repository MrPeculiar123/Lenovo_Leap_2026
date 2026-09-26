# PathForge

PathForge is a personalized learning navigator built with React, FastAPI, PostgreSQL, LangGraph, Gemini, and optional Pinecone grounding. It supports adaptive assessment, career gap analysis, grounded tutoring, seven-day plans, progress comparison, and persisted learner history.

## Local setup

Prerequisites: Docker Desktop, a PostgreSQL database, and a Gemini API key for live AI responses. Pinecone is optional; local educational content remains available without it.

1. Copy `server/.env.example` to `server/.env` or configure the root `.env` used by Docker.
2. Set a unique `JWT_SECRET_KEY`, `DATABASE_URL`, `FRONTEND_ORIGINS`, and `GOOGLE_API_KEY` or `GEMINI_API_KEY`.
3. Start the stack:

```powershell
docker compose up -d --build
```

4. Apply database migrations:

```powershell
docker compose exec server alembic upgrade head
```

5. Open `http://localhost:5173`. The API health checks are available at `http://localhost:8000/health` and `http://localhost:8000/api/navigator/health`.

## Testing

Offline backend contract tests run without Gemini or Pinecone:

```powershell
Push-Location server
pytest
Pop-Location
```

The client production bundle can be checked with:

```powershell
Push-Location client
npm install
npm run build
Pop-Location
```

Live vector and model checks require credentials and should be run separately from offline tests.

## Supported career pathways

The current data package supports the original onboarding paths: Data Analyst, Data Scientist, Software Engineer, AI Engineer, Cybersecurity Engineer, Product Manager, and Entrepreneur. Their benchmark profiles reuse grounded Python, SQL, statistics, and visualization concepts from the curriculum. Unsupported custom paths are rejected explicitly instead of silently receiving Data Analyst content.

## Security and deployment notes

- Keep JWT secrets and provider keys outside source control.
- Use HTTPS and a unique production JWT secret.
- Set `ENVIRONMENT=production`, a strict `FRONTEND_ORIGINS` list, and deployment-specific `ALLOWED_HOSTS` before production deployment.
- Bearer tokens are currently stored by the browser client; migrate to secure httpOnly cookies with CSRF protection before handling sensitive production workloads.
- External AI/vector calls use bounded retries and deterministic local fallbacks. Do not enable arbitrary code execution for coding questions in the API process.