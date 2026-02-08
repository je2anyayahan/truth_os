from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Load .env from repo root or api/ when present (Vercel uses env vars, no .env file)
_api_dir = Path(__file__).resolve().parent
_root = _api_dir.parent
for p in (_root / ".env", _api_dir / ".env"):
    if p.exists():
        load_dotenv(p)
        break

from ._lib.agent import default_agent
from ._lib.auth import User, get_user, require_operator
from ._lib.models import ContactMeetingsResponse, MeetingIngestRequest
from ._lib.storage import Storage, StorageConfig

APP_NAME = "truthOS-meeting-intelligence"

# CORS: set CORS_ORIGINS in Vercel. Regex allows any truth-os-app Vercel URL (prod + previews).
_cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
_cors_list = [o.strip() for o in _cors_origins.split(",") if o.strip()]
_cors_regex = re.compile(r"https://truth-os-app(-.*)?\.vercel\.app")


def _is_allowed_origin(origin: str | None) -> bool:
    if not origin:
        return False
    if origin in _cors_list:
        return True
    return bool(_cors_regex.fullmatch(origin))


class PreflightCORSMiddleware(BaseHTTPMiddleware):
    """Ensure OPTIONS preflight always returns CORS headers (runs first)."""

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method == "OPTIONS" and _is_allowed_origin(origin):
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "86400",
                },
            )
        response = await call_next(request)
        if origin and _is_allowed_origin(origin):
            response.headers.setdefault("Access-Control-Allow-Origin", origin)
            response.headers.setdefault("Access-Control-Allow-Credentials", "true")
        return response


app = FastAPI(title=APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_list,
    allow_origin_regex=r"https://truth-os-app(-.*)?\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)
app.add_middleware(PreflightCORSMiddleware)  # runs first: OPTIONS → 200 + CORS
router = FastAPI(title=APP_NAME)


def _storage() -> Storage:
    # Local: api/truthos.sqlite3. Vercel: /tmp (ephemeral; use a real DB for production).
    base = Path("/tmp") if os.environ.get("VERCEL") else Path(__file__).parent
    db_path = base / "truthos.sqlite3"
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


@router.get("")
@router.get("/")
def api_root():
    """So /api and /api/ return info; use /api/docs for Swagger."""
    return {
        "app": APP_NAME,
        "docs": "/api/docs",
        "openapi": "/api/openapi.json",
        "endpoints": ["POST /api/meetings", "POST /api/meetings/{meetingId}/analyze", "GET /api/contacts/{contactId}/meetings"],
    }


app.mount("/api", router)

