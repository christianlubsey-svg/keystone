# Keystone AI

Keystone AI is an education tool for college STEM learners. The current MVP lets a student paste study material, extracts target concepts and prerequisite foundations, asks for quick familiarity ratings, then returns a ranked scaffolding plan.

## Stack

- Backend: FastAPI
- Frontend: React, TypeScript, Vite
- AI: Anthropic Messages API from the backend

## Local Setup

1. Copy `.env.example` to `.env`.
2. Add `ANTHROPIC_API_KEY`.
3. Optionally set `ANTHROPIC_MODEL`; the default is `claude-sonnet-4-5-20250929`.
4. Start both services with Docker Compose:

```bash
docker compose up --build
```

The frontend runs at `http://localhost:5173` and the backend runs at `http://localhost:8000`.

## Development Checks

Backend:

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt
.\.venv\Scripts\python.exe -m pytest tests -q
```

Frontend:

```bash
cd frontend
npm install
npm run lint
node_modules\.bin\tsc.cmd -b --pretty false
```
