from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, Float, Text, DateTime, JSON
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./meetings.db")
DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    status = Column(String, default="pending")
    transcript = Column(Text, nullable=True)
    diarized_transcript = Column(Text, nullable=True)
    speakers = Column(JSON, nullable=True)
    action_items = Column(JSON, nullable=True)
    decisions = Column(JSON, nullable=True)
    open_questions = Column(JSON, nullable=True)
    follow_up_email = Column(Text, nullable=True)
    quality_score = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
