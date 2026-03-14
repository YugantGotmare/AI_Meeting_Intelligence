# ⚡ MeetingMind — Meeting Intelligence Layers

Upload a meeting recording. Get back structured intelligence: action items with owners, decisions made, open questions, and a ready-to-send follow-up email.

## Architecture

```
React Frontend
      ↓
FastAPI Backend
      ↓
LangGraph Agent
  ├── Node 1: Transcribe (Whisper API)
  ├── Node 2: Diarize (speaker labels)
  ├── Node 3: Extract intelligence (GPT-4o structured output)
  ├── Node 4: Quality check (self-critique loop)
  │     └── Retry if score < 0.6 (max 2 retries)
  └── Node 5: Generate follow-up email
      ↓
PostgreSQL (Railway) / SQLite (local)
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React + Vite |
| Backend | FastAPI (async) |
| Agent | LangGraph |
| Transcription | OpenAI Whisper |
| Intelligence | GPT-4o (structured JSON output) |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Hosting | Railway |
| CI/CD | GitHub Actions |

---

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Fill in OPENAI_API_KEY in .env

uvicorn app.main:app --reload
# → http://localhost:8000
# → Docs: http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install

# Create .env.local
echo "VITE_API_URL=http://localhost:8000" > .env.local

npm run dev
# → http://localhost:3000
```

### Run Tests

```bash
cd backend
pytest -v
```

---

## Deployment (Railway)

### Backend

1. Create a new Railway project
2. Add a PostgreSQL database service
3. Add a new service from your GitHub repo, set **root directory** to `backend`
4. Set environment variables in Railway dashboard:
   - `OPENAI_API_KEY`
   - `DATABASE_URL` (auto-injected by Railway Postgres plugin)
5. Railway uses `railway.json` to start the server automatically

### Frontend

Deploy to Vercel or Railway:
```bash
cd frontend
npm run build
# Deploy the dist/ folder
```

Set `VITE_API_URL` to your Railway backend URL.

### CI/CD Secrets

Add these to your GitHub repo → Settings → Secrets:
- `OPENAI_API_KEY` — for running tests
- `RAILWAY_TOKEN` — from Railway dashboard → Account Settings → Tokens

On every push to `main`:
1. CI runs tests
2. On success, auto-deploys to Railway

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/meetings/upload` | Upload audio file, returns `meeting_id` |
| GET | `/meetings/{id}` | Get meeting status + results |
| GET | `/meetings/` | List recent meetings |
| GET | `/health` | Health check |

---

## Project Structure

```
meeting-intelligence/
├── .github/workflows/
│   ├── ci.yml          # Test on every push/PR
│   └── deploy.yml      # Auto-deploy to Railway on main
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── agent/
│   │   │   ├── state.py    # AgentState TypedDict
│   │   │   ├── nodes.py    # LangGraph node functions
│   │   │   └── graph.py    # Graph definition + compile
│   │   ├── db/
│   │   │   └── database.py # SQLAlchemy models
│   │   └── routes/
│   │       └── meetings.py # FastAPI routes
│   └── tests/
├── frontend/
│   └── src/
│       └── App.jsx
└── README.md
```
