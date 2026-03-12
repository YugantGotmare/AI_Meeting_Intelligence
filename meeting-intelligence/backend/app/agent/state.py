from typing import TypedDict, Optional
from pydantic import BaseModel


class ActionItem(BaseModel):
    task: str
    owner: str
    deadline: Optional[str] = None
    priority: str = "medium"


class Decision(BaseModel):
    decision: str
    context: str
    made_by: Optional[str] = None


class MeetingIntelligence(BaseModel):
    action_items: list[ActionItem] = []
    decisions: list[Decision] = []
    open_questions: list[str] = []
    follow_up_email: Optional[str] = None


class AgentState(TypedDict):
    audio_file_path: str
    meeting_id: str
    transcript: Optional[str]
    diarized_transcript: Optional[str]
    speakers: Optional[list[str]]
    intelligence: Optional[MeetingIntelligence]
    follow_up_email: Optional[str]
    quality_score: Optional[float]
    retry_count: int
    error: Optional[str]
    status: str
