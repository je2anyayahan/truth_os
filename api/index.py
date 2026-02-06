from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from fastapi import Depends, FastAPI, HTTPException, status

# Load .env from repo root or api/ so OPENAI_API_KEY is available
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")
from fastapi.middleware.cors import CORSMiddleware

from ._lib.agent import default_agent
from ._lib.auth import User, get_user, require_operator
from ._lib.models import ContactMeetingsResponse, MeetingIngestRequest
from ._lib.storage import Storage, StorageConfig

APP_NAME = "truthOS-meeting-intelligence"

app = FastAPI(title=APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
router = FastAPI(title=APP_NAME)


def _storage() -> Storage:
    # SQLite file is local dev friendly; on Vercel, filesystem is ephemeral but ok for demo.
    db_path = Path(__file__).parent / "truthos.sqlite3"
    return Storage(StorageConfig(db_path=db_path))


@router.post("/meetings", status_code=status.HTTP_201_CREATED)
def ingest_meeting(
    body: MeetingIngestRequest,
    user: User = Depends(get_user),
):
    require_operator(user)
    store = _storage()
    try:
        record = store.insert_meeting_truth(body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return {
        "truth": record.model_dump(mode="json"),
        "derived": None,
        "note": "transcript stored as immutable truth; analysis is derived and separate",
    }


@router.post("/meetings/{meetingId}/analyze")
async def analyze_meeting(
    meetingId: str,
    user: User = Depends(get_user),
):
    require_operator(user)
    store = _storage()
    meeting = store.get_meeting_truth(meetingId)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="meeting not found")

    agent = default_agent()
    try:
        schema_v, prompt_v, model, derived = await agent.analyze(meeting.transcript)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    analysis = store.upsert_analysis_derived(
        meeting=meeting,
        schema_version=schema_v,
        prompt_version=prompt_v,
        model=model,
        derived=derived,
    )
    return {
        "truth_ref": {
            "meetingId": meeting.meetingId,
            "contactId": meeting.contactId,
            "transcriptHash": meeting.transcriptHash,
        },
        "analysis": analysis.model_dump(mode="json"),
        "note": "analysis is derived data; truth is immutable transcript/metadata",
    }


@router.get("/contacts/{contactId}/meetings", response_model=ContactMeetingsResponse)
def fetch_contact_meetings(
    contactId: str,
    user: User = Depends(get_user),
):
    store = _storage()
    meetings = store.list_contact_meetings_truth(contactId)
    analyses = store.list_contact_analyses(contactId)

    # Basic users can be restricted; for this simplified requirement we keep read-only
    # but still allow access. In a stricter version you could redact transcripts here.
    return ContactMeetingsResponse(contactId=contactId, meetings=meetings, analyses=analyses)


app.mount("/api", router)

