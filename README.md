# DoYin

DoYin is a local-first short-video platform MVP. It recreates the core flow of
a TikTok-style product: user registration and login, creator upload, background
video transcoding, HLS playback in an immersive feed, and admin moderation for
video visibility.

The repository is aimed at development, demos, and product iteration rather
than production deployment. The main happy path is:

1. A user registers and logs in.
2. A creator uploads a source video.
3. The backend accepts the upload immediately.
4. FFmpeg runs in the background and generates HLS segments plus a cover image.
5. Ready videos appear in the feed.
6. An admin can hide or restore videos from the moderation page.

## What This Project Includes

- Vue 3 frontend with an immersive vertical feed, login, registration, publish,
  and admin pages
- FastAPI backend with auth, feed, upload, playback, and moderation APIs
- PostgreSQL persistence for users, videos, and upload-job state
- FFmpeg-based media pipeline that converts uploaded source files into HLS
- Docker Compose setup for one-command local startup

## Core User Flows

- Authentication: users can register, log in, restore session state, and access
  protected routes
- Creator publish flow: authenticated users can upload a video with title and
  caption from the publish page
- Async processing: uploads return quickly while FFmpeg processing runs in the
  background
- Video feed: only videos that are ready and publicly visible are delivered to
  the feed
- Admin moderation: promoted admin users can inspect uploaded videos and change
  visibility between `public` and `hidden`

## Tech Stack

- Frontend: Vue 3, Vite, TypeScript, Pinia, Vue Router
- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Media pipeline: FFmpeg, HLS playlists, cover-image generation
- Local orchestration: Docker Compose

## Architecture Overview

- `frontend/`: SPA for login, registration, publish, immersive feed, and admin
  moderation
- `backend/`: FastAPI app with domain-oriented modules for auth, health, and
  videos
- `storage/`: local media output for original uploads, HLS assets, covers, and
  related runtime artifacts

## One-Command Docker Startup

### Prerequisites

- Docker
- Docker Compose

### Start Everything

```bash
docker compose up --build
```

On first startup, this will:

- start PostgreSQL
- build the backend image with FFmpeg installed
- build the frontend image
- run the frontend dev server and backend API with hot reload
- mount local source code and `storage/` into the containers

The frontend container runs `npm install` during startup, so the first boot can
take a little longer than later restarts.

### Run In Background

```bash
docker compose up --build -d
```

### Stop Services

```bash
docker compose down
```

### Stop And Remove Database Volume

```bash
docker compose down -v
```

Use `-v` only when you want to reset PostgreSQL data completely.

## Default Local URLs

| Service | URL | Notes |
| --- | --- | --- |
| Frontend app | `http://localhost:5173` | Main user interface |
| Backend API | `http://localhost:8000` | FastAPI server |
| API docs | `http://localhost:8000/docs` | Swagger UI from FastAPI |
| Health check | `http://localhost:8000/api/health` | Verifies API and database readiness |

## How To Use The App

### 1. Open The Frontend

Visit `http://localhost:5173`.

### 2. Create A User Account

- Open the registration page at `/register`
- Create a user with email, username, and password
- Sign in from `/login`

### 3. Upload A Video

- Go to `/publish`
- Select a video file
- Enter a title and optional caption
- Submit the upload

The backend responds immediately with an accepted upload job. The video is then
processed asynchronously into:

- an HLS manifest and segment set
- a generated cover image

### 4. Wait For Processing To Finish

The publish page polls upload-job status and shows whether the video is:

- `pending`
- `processing`
- `ready`
- `failed`

When the job reaches `ready`, the video becomes eligible for feed playback as
long as it is still publicly visible.

### 5. Browse The Feed

After login, open `/` to view the immersive video feed.

The feed:

- auto-loads authenticated content
- plays HLS video in a viewport-aligned experience
- keeps non-ready videos out of the public feed
- loads more pages as the user approaches the end of the current list

### 6. Promote An Admin User

To access the moderation page, promote an existing user to admin.

If you are using Docker:

```bash
docker compose exec backend python scripts/promote_admin.py --email you@example.com
```

Or by username:

```bash
docker compose exec backend python scripts/promote_admin.py --username yourname
```

After promotion, sign in again if needed and open `/admin/videos`.

### 7. Moderate Videos

The admin page lets you:

- inspect uploaded videos
- filter by keyword, processing status, and visibility
- hide public videos
- restore hidden videos

Only public videos with ready playback assets are eligible for the main feed.

## Local Development Without Docker

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Local Requirements For Non-Docker Development

- PostgreSQL running locally
- FFmpeg available on your machine path
- compatible Python and Node.js environments

## Configuration Notes

Docker Compose already provides working local defaults. If you want to override
ports or runtime settings, create a local `.env` file at the repository root
and define only the values you want to change.

Common variables include:

| Variable | Default | Purpose |
| --- | --- | --- |
| `FRONTEND_PORT` | `5173` | Frontend port |
| `BACKEND_PORT` | `8000` | Backend API port |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `doyin` | Database name |
| `POSTGRES_USER` | `doyin` | Database user |
| `POSTGRES_PASSWORD` | `doyin` | Database password |
| `JWT_SECRET_KEY` | local dev default | JWT signing secret |
| `FFMPEG_BINARY` | `ffmpeg` | FFmpeg executable name |
| `STORAGE_ROOT` | `./storage` or `/app/storage` in Docker | Local media root |

Media generated by uploads is stored under `storage/`, and the backend exposes
those files through public paths such as `/media/hls` and `/media/covers`.

## Useful Commands

```bash
docker compose up --build
docker compose up --build -d
docker compose logs -f backend
docker compose logs -f frontend
docker compose exec backend python scripts/promote_admin.py --email you@example.com
docker compose down
docker compose down -v
```

## Repository Notes

- HLS is the main playback path
- Upload requests are accepted before transcoding completes
- This repo is optimized for local development first, not production hardening

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
