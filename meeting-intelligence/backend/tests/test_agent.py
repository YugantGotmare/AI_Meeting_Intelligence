import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agent.nodes import (
    transcribe, diarize, extract_intelligence,
    quality_check, generate_email, should_retry
)
from app.agent.state import AgentState, MeetingIntelligence, ActionItem, Decision


def base_state(**overrides) -> AgentState:
    defaults = {
        "audio_file_path": "/tmp/test.mp3",
        "meeting_id": "test-123",
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
    return {**defaults, **overrides}


# ─── Transcribe ───────────────────────────────
@pytest.mark.asyncio
async def test_transcribe_success():
    mock_response = MagicMock()
    mock_response.text = "Hello, let's start the meeting."

    with patch("app.agent.nodes.client") as mock_client:
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        with patch("builtins.open", MagicMock()):
            state = base_state()
            result = await transcribe(state)

    assert result["transcript"] == "Hello, let's start the meeting."
    assert result["status"] == "transcribed"


@pytest.mark.asyncio
async def test_transcribe_failure():
    with patch("app.agent.nodes.client") as mock_client:
        mock_client.audio.transcriptions.create = AsyncMock(
            side_effect=Exception("API error")
        )
        with patch("builtins.open", MagicMock()):
            state = base_state()
            result = await transcribe(state)

    assert result["status"] == "failed"
    assert "Transcription failed" in result["error"]


# ─── Extract Intelligence ─────────────────────
@pytest.mark.asyncio
async def test_extract_intelligence_success():
    mock_json = {
        "action_items": [
            {"task": "Write report", "owner": "Alice", "deadline": "Friday", "priority": "high"}
        ],
        "decisions": [
            {"decision": "Use PostgreSQL", "context": "For scalability", "made_by": "Bob"}
        ],
        "open_questions": ["What is the budget?"]
    }

    mock_response = MagicMock()
    mock_response.choices[0].message.content = __import__("json").dumps(mock_json)

    with patch("app.agent.nodes.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        state = base_state(transcript="Alice: I'll write the report by Friday.", status="diarized")
        result = await extract_intelligence(state)

    assert result["status"] == "extracted"
    assert len(result["intelligence"].action_items) == 1
    assert result["intelligence"].action_items[0].owner == "Alice"
    assert len(result["intelligence"].decisions) == 1
    assert len(result["intelligence"].open_questions) == 1


# ─── Quality Check ────────────────────────────
@pytest.mark.asyncio
async def test_quality_check_high_score():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"score": 0.9, "issues": []}'

    intelligence = MeetingIntelligence(
        action_items=[ActionItem(task="Deploy app", owner="Alice")],
        decisions=[Decision(decision="Use React", context="Team voted")],
        open_questions=[]
    )

    with patch("app.agent.nodes.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        state = base_state(
            transcript="Alice: I'll deploy the app.",
            intelligence=intelligence,
            status="extracted"
        )
        result = await quality_check(state)

    assert result["quality_score"] == 0.9
    assert result["status"] == "checked"


# ─── Should Retry Logic ───────────────────────
def test_should_retry_when_low_score():
    state = base_state(quality_score=0.4, retry_count=0, status="checked")
    assert should_retry(state) == "retry"


def test_should_proceed_when_high_score():
    state = base_state(quality_score=0.8, retry_count=0, status="checked")
    assert should_retry(state) == "proceed"


def test_should_proceed_when_max_retries_reached():
    state = base_state(quality_score=0.3, retry_count=2, status="checked")
    assert should_retry(state) == "proceed"


def test_should_fail_on_failed_status():
    state = base_state(status="failed", error="Something went wrong")
    assert should_retry(state) == "failed"


# ─── Generate Email ───────────────────────────
@pytest.mark.asyncio
async def test_generate_email():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Subject: Meeting Follow-up\n\nHi team..."

    intelligence = MeetingIntelligence(
        action_items=[ActionItem(task="Deploy app", owner="Alice", deadline="Monday")],
        decisions=[Decision(decision="Use React", context="Team voted")],
        open_questions=["What is the timeline?"]
    )

    with patch("app.agent.nodes.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        state = base_state(intelligence=intelligence, status="checked", quality_score=0.9)
        result = await generate_email(state)

    assert result["follow_up_email"].startswith("Subject:")
    assert result["status"] == "done"