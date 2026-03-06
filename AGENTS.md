# AGENTS.md — RFP Copilot

## 1. Source of Truth
1. User request
2. `planning_document.md`
3. `PROJECT_CONTEXT.md`
4. `README.md`
5. `ARCHITECTURE.md`

## 2. Monorepo Layout
- `api/`: FastAPI, SQLAlchemy, Alembic
- `web/`: Next.js App Router, TypeScript
- `data/`: SQLite DB, uploads, exports
- `scripts/`: local dev shortcuts

## 3. Working Rules
- Keep API routes under `/api/*`.
- Use `DATABASE_URL` with SQLite default and keep Postgres migration path open.
- Prefer minimal diffs and preserve scaffold shape from `planning_document.md`.
- Put frontend API access behind `web/lib/api.ts`.
- Do not hardcode secrets; use `.env` files only.
- For placeholder modules, keep them import-safe so the repo stays runnable.

## 4. Commands
- API install: `cd api && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- API run: `cd api && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000`
- Web install: `cd web && npm install`
- Web run: `cd web && npm run dev`
- API syntax check: `cd api && source .venv/bin/activate && python -m compileall app`
- Web typecheck: `cd web && npm run typecheck`

## 5. Current Priorities
1. Evidence visibility and manual source adjustment for RFP extraction chunks
2. Section-level source pinning before draft generation
3. Mapping/export polish after the core writing loop works

## 6. Documentation Triggers
- Setup/env change: update `README.md` and `PROJECT_CONTEXT.md`
- Folder or data-flow change: update `ARCHITECTURE.md` and `PROJECT_CONTEXT.md`
- Workflow or agent-rules change: update this file
