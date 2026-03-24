from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.database import init_db
from app.routes.meetings import router as meetings_router
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Meeting Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meetings_router)
if os.path.exists("static"):
    app.mount("/app", StaticFiles(directory="static", html=True), name="static")

    @app.get("/app/{full_path:path}")
    async def serve_frontend(full_path: str):
        return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}
