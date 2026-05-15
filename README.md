# TasteCraft

AI content engine with taste evolution — co-create content that sounds like you.

## Architecture

```
tastecraft/
├── backend/          # FastAPI + Celery + PostgreSQL
├── frontend/         # Vite + React 19 + Tailwind 4
├── docs/prd/         # Product requirements
└── .archive/         # Legacy code for reference
```

## Quick Start

```bash
# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload

# Frontend
cd frontend
pnpm install
pnpm dev
```

## Tech Stack

- **Backend**: FastAPI, Pydantic v2, PostgreSQL, Celery, Redis
- **Frontend**: React 19, TypeScript, Tailwind CSS 4, Vite
- **AI**: Anthropic Claude SDK
- **Browser**: Camoufox (anti-detect), Playwright
- **Data**: TikHub API, wechatpy
