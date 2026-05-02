# AGENTS.md

## Project overview
This repository builds a web short-video platform MVP.
Frontend: Vue 3 + Vite + TypeScript + Pinia + Vue Router
Backend: FastAPI + SQLAlchemy + PostgreSQL
Media pipeline: upload original video -> FFmpeg transcode to HLS -> serve HLS for playback
Deployment target: local development first via Docker Compose

## Engineering rules
- Prefer small, reviewable commits.
- Avoid introducing new dependencies unless justified in design.md.
- Keep backend modules separated by domain.
- Do not block upload requests on long-running transcode work.
- Prefer HLS playback over raw MP4 for the main player path.

## Commands
- Frontend install: cd frontend && npm install
- Frontend dev: cd frontend && npm run dev
- Frontend build: cd frontend && npm run build
- Backend install: cd backend && pip install -r requirements.txt
- Backend dev: cd backend && uvicorn app.main:app --reload
- Backend test: cd backend && pytest
- Full stack local: docker compose up --build

## Done criteria
- Code compiles
- Relevant tests pass
- Documentation is updated when behavior changes
- API and UI behavior match the implemented product flow
