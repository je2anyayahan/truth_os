from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MeetingType = Literal["sales", "coaching"]


class MeetingIngestRequest(BaseModel):
    meetingId: str = Field(min_length=1)
    contactId: str = Field(min_length=1)
    type: MeetingType
    occurredAt: datetime
    transcript: str = Field(min_length=1)


class MeetingRecord(BaseModel):
    meetingId: str
    contactId: str
    type: MeetingType
    occurredAt: datetime
    transcript: str
    transcriptHash: str
    createdAt: datetime


Sentiment = Literal["very_negative", "negative", "neutral", "positive", "very_positive"]
Outcome = Literal["advanced", "stalled", "closed_won", "closed_lost", "unknown"]


class MeetingAnalysisData(BaseModel):
    topics: list[str] = Field(default_factory=list, max_length=25)
    objections: list[str] = Field(default_factory=list, max_length=25)
    commitments: list[str] = Field(default_factory=list, max_length=25)
    sentiment: Sentiment
    outcome: Outcome
    summary: str = Field(min_length=1, max_length=1200)


class MeetingAnalysisRecord(BaseModel):
    meetingId: str
    contactId: str
    transcriptHash: str
    schemaVersion: str
    promptVersion: str
    model: str
    analyzedAt: datetime
    derived: MeetingAnalysisData


class ContactMeetingsResponse(BaseModel):
    contactId: str
    meetings: list[MeetingRecord]
    analyses: list[MeetingAnalysisRecord]

