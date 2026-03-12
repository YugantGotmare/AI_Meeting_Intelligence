@echo off
echo Creating Meeting Intelligence project...

:: ─── Directory Structure ───────────────────────────────────────
mkdir meeting-intelligence\.github\workflows
mkdir meeting-intelligence\backend\app\routes
mkdir meeting-intelligence\backend\app\agent
mkdir meeting-intelligence\backend\app\db
mkdir meeting-intelligence\backend\app\services
mkdir meeting-intelligence\backend\tests
mkdir meeting-intelligence\frontend\src\components

:: ─── __init__.py files ─────────────────────────────────────────
type nul > meeting-intelligence\backend\app\__init__.py
type nul > meeting-intelligence\backend\app\routes\__init__.py
type nul > meeting-intelligence\backend\app\agent\__init__.py
type nul > meeting-intelligence\backend\app\db\__init__.py
type nul > meeting-intelligence\backend\app\services\__init__.py
type nul > meeting-intelligence\backend\tests\__init__.py

:: ─── state.py ──────────────────────────────────────────────────
(
echo from typing import TypedDict, Optional
echo from pydantic import BaseModel
echo.
echo.
echo class ActionItem^(BaseModel^):
echo     task: str
echo     owner: str
echo     deadline: Optional[str] = None
echo     priority: str = "medium"
echo.
echo.
echo class Decision^(BaseModel^):
echo     decision: str
echo     context: str
echo     made_by: Optional[str] = None
echo.
echo.
echo class MeetingIntelligence^(BaseModel^):
echo     action_items: list[ActionItem] = []
echo     decisions: list[Decision] = []
echo     open_questions: list[str] = []
echo     follow_up_email: Optional[str] = None
echo.
echo.
echo class AgentState^(TypedDict^):
echo     audio_file_path: str
echo     meeting_id: str
echo     transcript: Optional[str]
echo     diarized_transcript: Optional[str]
echo     speakers: Optional[list[str]]
echo     intelligence: Optional[MeetingIntelligence]
echo     follow_up_email: Optional[str]
echo     quality_score: Optional[float]
echo     retry_count: int
echo     error: Optional[str]
echo     status: str
) > meeting-intelligence\backend\app\agent\state.py

:: ─── graph.py ──────────────────────────────────────────────────
(
echo from langgraph.graph import StateGraph, END
echo from app.agent.state import AgentState
echo from app.agent.nodes import ^(
echo     transcribe, diarize, extract_intelligence,
echo     quality_check, generate_email, should_retry,
echo ^)
echo.
echo.
echo def increment_retry^(state: AgentState^) -^> AgentState:
echo     return {**state, "retry_count": state.get^("retry_count", 0^) + 1}
echo.
echo.
echo def build_graph^(^) -^> StateGraph:
echo     graph = StateGraph^(AgentState^)
echo     graph.add_node^("transcribe", transcribe^)
echo     graph.add_node^("diarize", diarize^)
echo     graph.add_node^("extract_intelligence", extract_intelligence^)
echo     graph.add_node^("quality_check", quality_check^)
echo     graph.add_node^("increment_retry", increment_retry^)
echo     graph.add_node^("generate_email", generate_email^)
echo     graph.set_entry_point^("transcribe"^)
echo     graph.add_edge^("transcribe", "diarize"^)
echo     graph.add_edge^("diarize", "extract_intelligence"^)
echo     graph.add_edge^("extract_intelligence", "quality_check"^)
echo     graph.add_conditional_edges^(
echo         "quality_check", should_retry,
echo         {"retry": "increment_retry", "proceed": "generate_email", "failed": END}
echo     ^)
echo     graph.add_edge^("increment_retry", "extract_intelligence"^)
echo     graph.add_edge^("generate_email", END^)
echo     return graph.compile^(^)
echo.
echo.
echo meeting_agent = build_graph^(^)
) > meeting-intelligence\backend\app\agent\graph.py

:: ─── main.py ───────────────────────────────────────────────────
(
echo from fastapi import FastAPI
echo from fastapi.middleware.cors import CORSMiddleware
echo from contextlib import asynccontextmanager
echo from app.db.database import init_db
echo from app.routes.meetings import router as meetings_router
echo.
echo.
echo @asynccontextmanager
echo async def lifespan^(app: FastAPI^):
echo     await init_db^(^)
echo     yield
echo.
echo.
echo app = FastAPI^(
echo     title="Meeting Intelligence API",
echo     version="1.0.0",
echo     lifespan=lifespan,
echo ^)
echo.
echo app.add_middleware^(
echo     CORSMiddleware,
echo     allow_origins=["*"],
echo     allow_credentials=True,
echo     allow_methods=["*"],
echo     allow_headers=["*"],
echo ^)
echo.
echo app.include_router^(meetings_router^)
echo.
echo.
echo @app.get^("/health"^)
echo async def health^(^):
echo     return {"status": "ok"}
) > meeting-intelligence\backend\app\main.py

:: ─── database.py ───────────────────────────────────────────────
(
echo from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
echo from sqlalchemy.orm import sessionmaker, DeclarativeBase
echo from sqlalchemy import Column, String, Float, Text, DateTime, JSON
echo from datetime import datetime
echo import os
echo.
echo DATABASE_URL = os.getenv^("DATABASE_URL", "sqlite+aiosqlite:///./meetings.db"^)
echo DATABASE_URL = DATABASE_URL.replace^("postgres://", "postgresql+asyncpg://"^)
echo.
echo engine = create_async_engine^(DATABASE_URL, echo=False^)
echo AsyncSessionLocal = sessionmaker^(engine, class_=AsyncSession, expire_on_commit=False^)
echo.
echo.
echo class Base^(DeclarativeBase^):
echo     pass
echo.
echo.
echo class Meeting^(Base^):
echo     __tablename__ = "meetings"
echo     id = Column^(String, primary_key=True^)
echo     filename = Column^(String, nullable=False^)
echo     status = Column^(String, default="pending"^)
echo     transcript = Column^(Text, nullable=True^)
echo     diarized_transcript = Column^(Text, nullable=True^)
echo     speakers = Column^(JSON, nullable=True^)
echo     action_items = Column^(JSON, nullable=True^)
echo     decisions = Column^(JSON, nullable=True^)
echo     open_questions = Column^(JSON, nullable=True^)
echo     follow_up_email = Column^(Text, nullable=True^)
echo     quality_score = Column^(Float, nullable=True^)
echo     error = Column^(Text, nullable=True^)
echo     created_at = Column^(DateTime, default=datetime.utcnow^)
echo     updated_at = Column^(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow^)
echo.
echo.
echo async def get_db^(^):
echo     async with AsyncSessionLocal^(^) as session:
echo         yield session
echo.
echo.
echo async def init_db^(^):
echo     async with engine.begin^(^) as conn:
echo         await conn.run_sync^(Base.metadata.create_all^)
) > meeting-intelligence\backend\app\db\database.py

:: ─── requirements.txt ──────────────────────────────────────────
(
echo fastapi==0.115.0
echo uvicorn[standard]==0.30.6
echo openai==1.51.0
echo langgraph==0.2.28
echo langchain-core==0.3.10
echo sqlalchemy==2.0.35
echo aiosqlite==0.20.0
echo asyncpg==0.29.0
echo python-multipart==0.0.12
echo pydantic==2.9.2
echo httpx==0.27.2
) > meeting-intelligence\backend\requirements.txt

:: ─── railway.json ──────────────────────────────────────────────
(
echo {
echo   "$schema": "https://railway.app/railway.schema.json",
echo   "build": { "builder": "NIXPACKS" },
echo   "deploy": {
echo     "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
echo     "healthcheckPath": "/health",
echo     "healthcheckTimeout": 30,
echo     "restartPolicyType": "ON_FAILURE",
echo     "restartPolicyMaxRetries": 3
echo   }
echo }
) > meeting-intelligence\backend\railway.json

:: ─── pytest.ini ────────────────────────────────────────────────
(
echo [pytest]
echo asyncio_mode = auto
echo testpaths = tests
) > meeting-intelligence\backend\pytest.ini

:: ─── .env.example ──────────────────────────────────────────────
(
echo OPENAI_API_KEY=sk-...
echo DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
) > meeting-intelligence\backend\.env.example

:: ─── ci.yml ────────────────────────────────────────────────────
(
echo name: CI
echo on:
echo   push:
echo     branches: [main, develop]
echo   pull_request:
echo     branches: [main]
echo jobs:
echo   test:
echo     runs-on: ubuntu-latest
echo     defaults:
echo       run:
echo         working-directory: backend
echo     env:
echo       OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
echo       DATABASE_URL: sqlite+aiosqlite:///./test.db
echo     steps:
echo       - uses: actions/checkout@v4
echo       - name: Set up Python
echo         uses: actions/setup-python@v5
echo         with:
echo           python-version: "3.11"
echo           cache: "pip"
echo           cache-dependency-path: backend/requirements.txt
echo       - name: Install dependencies
echo         run: pip install -r requirements.txt pytest pytest-asyncio httpx
echo       - name: Run tests
echo         run: pytest --tb=short -v
) > meeting-intelligence\.github\workflows\ci.yml

:: ─── deploy.yml ────────────────────────────────────────────────
(
echo name: Deploy to Railway
echo on:
echo   push:
echo     branches: [main]
echo jobs:
echo   deploy:
echo     runs-on: ubuntu-latest
echo     steps:
echo       - uses: actions/checkout@v4
echo       - name: Install Railway CLI
echo         run: npm install -g @railway/cli
echo       - name: Deploy to Railway
echo         env:
echo           RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
echo         run: ^|
echo           cd backend
echo           railway up --service meeting-intelligence-backend --detach
) > meeting-intelligence\.github\workflows\deploy.yml

:: ─── frontend files ────────────────────────────────────────────
(
echo {
echo   "name": "meeting-intelligence-frontend",
echo   "version": "1.0.0",
echo   "type": "module",
echo   "scripts": {
echo     "dev": "vite",
echo     "build": "vite build",
echo     "preview": "vite preview"
echo   },
echo   "dependencies": {
echo     "react": "^18.3.1",
echo     "react-dom": "^18.3.1"
echo   },
echo   "devDependencies": {
echo     "@vitejs/plugin-react": "^4.3.1",
echo     "vite": "^5.4.8"
echo   }
echo }
) > meeting-intelligence\frontend\package.json

(
echo import { defineConfig } from "vite";
echo import react from "@vitejs/plugin-react";
echo export default defineConfig^({
echo   plugins: [react^(^)],
echo   server: { port: 3000 },
echo }^);
) > meeting-intelligence\frontend\vite.config.js

(
echo ^<!DOCTYPE html^>
echo ^<html lang="en"^>
echo   ^<head^>
echo     ^<meta charset="UTF-8" /^>
echo     ^<meta name="viewport" content="width=device-width, initial-scale=1.0" /^>
echo     ^<title^>MeetingMind^</title^>
echo     ^<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700^&display=swap" rel="stylesheet" /^>
echo     ^<style^>*, *::before, *::after { box-sizing: border-box; } body { margin: 0; }^</style^>
echo   ^</head^>
echo   ^<body^>
echo     ^<div id="root"^>^</div^>
echo     ^<script type="module" src="/src/main.jsx"^>^</script^>
echo   ^</body^>
echo ^</html^>
) > meeting-intelligence\frontend\index.html

(
echo import { StrictMode } from "react";
echo import { createRoot } from "react-dom/client";
echo import App from "./App.jsx";
echo createRoot^(document.getElementById^("root"^)^).render^(
echo   ^<StrictMode^>^<App /^>^</StrictMode^>
echo ^);
) > meeting-intelligence\frontend\src\main.jsx

:: ─── Placeholder files (paste content from Claude) ─────────────
echo # Paste content from nodes.py > meeting-intelligence\backend\app\agent\nodes.py
echo # Paste content from meetings.py > meeting-intelligence\backend\app\routes\meetings.py
echo # Paste content from test_agent.py > meeting-intelligence\backend\tests\test_agent.py
echo # Paste content from test_routes.py > meeting-intelligence\backend\tests\test_routes.py
echo # Paste content from App.jsx > meeting-intelligence\frontend\src\App.jsx

echo.
echo ✅ Project structure created!
echo.
echo Next steps:
echo   1. cd meeting-intelligence
echo   2. Paste content into nodes.py, meetings.py, test files, and App.jsx
echo   3. cd backend ^&^& python -m venv venv ^&^& venv\Scripts\activate
echo   4. pip install -r requirements.txt
echo   5. copy .env.example .env  ^(then add your OPENAI_API_KEY^)
echo   6. uvicorn app.main:app --reload
echo.
pause