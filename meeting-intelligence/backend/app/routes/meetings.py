import uuid
import os
import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import Meeting, get_db
from app.agent.graph import meeting_agent

router = APIRouter(prefix="/meetings", tags=["meetings"])

UPLOAD_DIR = "/tmp/meeting_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".webm", ".ogg"}


async def run_agent(meeting_id: str, file_path: str):
    """Background task — runs the LangGraph agent and saves results to DB."""
    from app.db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # Mark as processing
        result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
        meeting = result.scalar_one_or_none()
        if not meeting:
            return

        meeting.status = "processing"
        await db.commit()

        try:
            initial_state = {
                "audio_file_path": file_path,
                "meeting_id": meeting_id,
                "transcript": None,
                "diarized_transcript": None,
                "speakers": None,
                "intelligence": None,
                "follow_up_email": None,
                "quality_score": None,
                "retry_count": 0,
                "error": None,
                "status": "starting",
            }

            final_state = await meeting_agent.ainvoke(initial_state)

            # Save everything to DB
            meeting.status = final_state.get("status", "done")
            meeting.transcript = final_state.get("transcript")
            meeting.diarized_transcript = final_state.get("diarized_transcript")
            meeting.speakers = final_state.get("speakers")
            meeting.follow_up_email = final_state.get("follow_up_email")
            meeting.quality_score = final_state.get("quality_score")
            meeting.error = final_state.get("error")

            intelligence = final_state.get("intelligence")
            if intelligence:
                meeting.action_items = [item.model_dump() for item in intelligence.action_items]
                meeting.decisions = [d.model_dump() for d in intelligence.decisions]
                meeting.open_questions = intelligence.open_questions

            await db.commit()

        except Exception as e:
            meeting.status = "failed"
            meeting.error = str(e)
            await db.commit()

        finally:
            # Clean up uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)


@router.post("/upload")
async def upload_meeting(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # Validate file type
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Save file
    meeting_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{meeting_id}{ext}")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Create DB record
    meeting = Meeting(
        id=meeting_id,
        filename=file.filename,
        status="pending"
    )
    db.add(meeting)
    await db.commit()

    # Kick off agent in background
    background_tasks.add_task(run_agent, meeting_id, file_path)

    return {"meeting_id": meeting_id, "status": "pending"}


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return {
        "id": meeting.id,
        "filename": meeting.filename,
        "status": meeting.status,
        "speakers": meeting.speakers,
        "action_items": meeting.action_items,
        "decisions": meeting.decisions,
        "open_questions": meeting.open_questions,
        "follow_up_email": meeting.follow_up_email,
        "quality_score": meeting.quality_score,
        "transcript": meeting.transcript,
        "error": meeting.error,
        "created_at": meeting.created_at.isoformat() if meeting.created_at else None,
    }


@router.get("/")
async def list_meetings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Meeting).order_by(Meeting.created_at.desc()).limit(20))
    meetings = result.scalars().all()

    return [
        {
            "id": m.id,
            "filename": m.filename,
            "status": m.status,
            "quality_score": m.quality_score,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in meetings
    ]