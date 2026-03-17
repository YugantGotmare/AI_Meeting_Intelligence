import json
import re
import os
from openai import AsyncOpenAI
import google.generativeai as genai
from app.agent.state import AgentState, MeetingIntelligence, ActionItem, Decision
from langchain_groq import ChatGroq

# Whisper still uses OpenAI (best in class for transcription)
whisper_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# All LLM calls use Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini = genai.GenerativeModel("gemini-2.0-flash-lite")

# Groq for all LLM calls
llm = ChatGroq(
    model="llama-3.3-70b-versatile",  # fast, free, excellent quality
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1
)

MAX_RETRIES = 2

async def _llm(prompt: str) -> str:
    response = await llm.ainvoke(prompt)  # native async, no executor needed
    return response.content

async def _gemini(prompt: str) -> str:
    import asyncio
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: gemini.generate_content(prompt)
    )
    return response.text


# ─────────────────────────────────────────────
# Node 1: Transcribe audio using Whisper
# ─────────────────────────────────────────────
async def transcribe(state: AgentState) -> AgentState:
    try:
        file_path = state["audio_file_path"]

        if os.path.getsize(file_path) > 24 * 1024 * 1024:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(file_path)
            compressed_path = file_path + "_compressed.mp3"
            audio.export(compressed_path, format="mp3", bitrate="64k")
            file_path = compressed_path

        with open(file_path, "rb") as f:
            response = await whisper_client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )

        return {**state, "transcript": response.text, "status": "transcribed"}

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

    # diarized = await _gemini(prompt)
    diarized = await _llm(prompt)

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

You MUST return valid JSON only. No markdown, no explanation, no code fences — just the raw JSON object.

Extract:
1. action_items: specific tasks assigned to people
2. decisions: things that were decided/agreed upon
3. open_questions: things raised but not resolved

JSON schema:
{{
  "action_items": [
    {{
      "task": "string",
      "owner": "string (use Unknown if unclear)",
      "deadline": "string or null",
      "priority": "low | medium | high"
    }}
  ],
  "decisions": [
    {{
      "decision": "string",
      "context": "string",
      "made_by": "string or null"
    }}
  ],
  "open_questions": ["string"]
}}

Meeting transcript:
{transcript}"""

    # raw = await _gemini(prompt)
    raw = await _llm(prompt)

    try:
        clean = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(clean)
        intelligence = MeetingIntelligence(
            action_items=[ActionItem(**item) for item in data.get("action_items", [])],
            decisions=[Decision(**d) for d in data.get("decisions", [])],
            open_questions=data.get("open_questions", [])
        )
        return {**state, "intelligence": intelligence, "status": "extracted"}
    except Exception as e:
        return {**state, "error": f"Extraction parsing failed: {str(e)}", "status": "failed"}


# ─────────────────────────────────────────────
# Node 4: Quality check
# ─────────────────────────────────────────────
async def quality_check(state: AgentState) -> AgentState:
    if state.get("status") == "failed":
        return state

    intelligence = state["intelligence"]
    transcript = state.get("diarized_transcript") or state["transcript"]

    prompt = f"""You are a quality checker for meeting intelligence extraction.

Score the quality from 0.0 to 1.0 based on:
- Are action items specific with clear owners?
- Are decisions accurately captured?
- Are open questions real questions from the meeting?

Original transcript:
{transcript}

Extracted intelligence:
{intelligence.model_dump_json(indent=2)}

Return raw JSON only, no markdown:
{{
  "score": 0.0-1.0,
  "issues": ["list of issues if any"]
}}"""

    # raw = await _gemini(prompt)
    raw = await _llm(prompt)

    try:
        clean = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(clean)
        score = float(data.get("score", 0.5))
    except Exception:
        score = 0.5

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

    decisions_text = "\n".join([f"- {d.decision}" for d in intelligence.decisions]) or "None"
    questions_text = "\n".join([f"- {q}" for q in intelligence.open_questions]) or "None"

    prompt = f"""Write a professional follow-up email summarizing this meeting.
Tone: clear, concise, professional.

ACTION ITEMS:
{action_items_text}

DECISIONS MADE:
{decisions_text}

OPEN QUESTIONS:
{questions_text}

Start with "Subject: ..." """

    # email = await _gemini(prompt)
    email = await _llm(prompt)
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