import json
import re
import os
from openai import AsyncOpenAI
from app.agent.state import AgentState, MeetingIntelligence, ActionItem, Decision

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_RETRIES = 2


# ─────────────────────────────────────────────
# Node 1: Transcribe audio using Whisper
# ─────────────────────────────────────────────
async def transcribe(state: AgentState) -> AgentState:
    try:
        with open(state["audio_file_path"], "rb") as f:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",  # gives us word-level timestamps
                timestamp_granularities=["segment"]
            )

        transcript = response.text
        return {**state, "transcript": transcript, "status": "transcribed"}

    except Exception as e:
        return {**state, "error": f"Transcription failed: {str(e)}", "status": "failed"}


# ─────────────────────────────────────────────
# Node 2: Diarize — add speaker labels
# ─────────────────────────────────────────────
async def diarize(state: AgentState) -> AgentState:
    if state.get("status") == "failed":
        return state

    transcript = state["transcript"]

    prompt = f"""You are analyzing a meeting transcript. Your job is to identify different speakers and label them.

Rules:
- Label speakers as Speaker A, Speaker B, etc. (or use names if mentioned)
- Each line should start with the speaker label followed by a colon
- Keep the original words exactly as they are
- If you cannot distinguish speakers, label everything as "Speaker A"

Transcript:
{transcript}

Return ONLY the labeled transcript, nothing else."""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )

    diarized = response.choices[0].message.content

    # Extract unique speaker names
    speakers = list(set(re.findall(r'^(Speaker [A-Z]|[\w\s]+):', diarized, re.MULTILINE)))
    speakers = [s.strip() for s in speakers if s.strip()]

    return {**state, "diarized_transcript": diarized, "speakers": speakers, "status": "diarized"}


# ─────────────────────────────────────────────
# Node 3: Extract actions, decisions, questions
# ─────────────────────────────────────────────
async def extract_intelligence(state: AgentState) -> AgentState:
    if state.get("status") == "failed":
        return state

    transcript = state.get("diarized_transcript") or state["transcript"]

    prompt = f"""You are an expert meeting analyst. Extract structured intelligence from this meeting transcript.

You MUST return valid JSON only. No markdown, no explanation — just the JSON object.

Extract:
1. action_items: specific tasks assigned to people (include who, what, and deadline if mentioned)
2. decisions: things that were decided/agreed upon
3. open_questions: things raised but not resolved

JSON schema:
{{
  "action_items": [
    {{
      "task": "string — what needs to be done",
      "owner": "string — who is responsible (use 'Unknown' if unclear)",
      "deadline": "string or null — when it's due",
      "priority": "low | medium | high"
    }}
  ],
  "decisions": [
    {{
      "decision": "string — what was decided",
      "context": "string — why or how",
      "made_by": "string or null"
    }}
  ],
  "open_questions": ["string"]
}}

Meeting transcript:
{transcript}"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    raw = response.choices[0].message.content

    try:
        data = json.loads(raw)
        intelligence = MeetingIntelligence(
            action_items=[ActionItem(**item) for item in data.get("action_items", [])],
            decisions=[Decision(**d) for d in data.get("decisions", [])],
            open_questions=data.get("open_questions", [])
        )
        return {**state, "intelligence": intelligence, "status": "extracted"}
    except Exception as e:
        return {**state, "error": f"Extraction parsing failed: {str(e)}", "status": "failed"}


# ─────────────────────────────────────────────
# Node 4: Quality check — score the extraction
# ─────────────────────────────────────────────
async def quality_check(state: AgentState) -> AgentState:
    if state.get("status") == "failed":
        return state

    intelligence = state["intelligence"]
    transcript = state.get("diarized_transcript") or state["transcript"]

    prompt = f"""You are a quality checker for meeting intelligence extraction.

Given the original transcript and the extracted intelligence, score the quality from 0.0 to 1.0.

Consider:
- Are action items specific enough? Do they have clear owners?
- Are decisions accurately captured?
- Are open questions real questions from the meeting?
- Is anything important missed?

Original transcript:
{transcript}

Extracted intelligence:
{intelligence.model_dump_json(indent=2)}

Return JSON only:
{{
  "score": 0.0-1.0,
  "issues": ["list of issues if any"]
}}"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    data = json.loads(response.choices[0].message.content)
    score = float(data.get("score", 0.5))

    return {**state, "quality_score": score, "status": "checked"}


# ─────────────────────────────────────────────
# Node 5: Generate follow-up email
# ─────────────────────────────────────────────
async def generate_email(state: AgentState) -> AgentState:
    if state.get("status") == "failed":
        return state

    intelligence = state["intelligence"]

    action_items_text = "\n".join(
        [f"- {item.owner}: {item.task}" + (f" (by {item.deadline})" if item.deadline else "")
         for item in intelligence.action_items]
    ) or "None"

    decisions_text = "\n".join(
        [f"- {d.decision}" for d in intelligence.decisions]
    ) or "None"

    questions_text = "\n".join(
        [f"- {q}" for q in intelligence.open_questions]
    ) or "None"

    prompt = f"""Write a professional follow-up email summarizing this meeting.

Tone: clear, concise, professional. No fluff.

Data:
ACTION ITEMS:
{action_items_text}

DECISIONS MADE:
{decisions_text}

OPEN QUESTIONS:
{questions_text}

Write the email with subject line included. Start with "Subject: ..."."""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    email = response.choices[0].message.content
    return {**state, "follow_up_email": email, "status": "done"}


# ─────────────────────────────────────────────
# Conditional edge: retry or proceed
# ─────────────────────────────────────────────
def should_retry(state: AgentState) -> str:
    if state.get("status") == "failed":
        return "failed"

    score = state.get("quality_score", 0)
    retry_count = state.get("retry_count", 0)

    if score < 0.6 and retry_count < MAX_RETRIES:
        return "retry"

    return "proceed"