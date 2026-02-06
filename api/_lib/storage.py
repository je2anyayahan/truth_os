from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .models import (
    MeetingAnalysisData,
    MeetingAnalysisRecord,
    MeetingIngestRequest,
    MeetingRecord,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StorageConfig:
    db_path: Path


class Storage:
    """
    Truth vs Derived:
    - meetings/transcripts are immutable truth records
    - analyses are derived records stored separately and can be recomputed/versioned
    """

    def __init__(self, cfg: StorageConfig):
        self._cfg = cfg
        self._cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._cfg.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meetings_truth (
                  meeting_id TEXT PRIMARY KEY,
                  contact_id TEXT NOT NULL,
                  type TEXT NOT NULL,
                  occurred_at TEXT NOT NULL,
                  transcript TEXT NOT NULL,
                  transcript_hash TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS meeting_analysis_derived (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  meeting_id TEXT NOT NULL,
                  contact_id TEXT NOT NULL,
                  transcript_hash TEXT NOT NULL,
                  schema_version TEXT NOT NULL,
                  prompt_version TEXT NOT NULL,
                  model TEXT NOT NULL,
                  derived_json TEXT NOT NULL,
                  analyzed_at TEXT NOT NULL,
                  UNIQUE(meeting_id, transcript_hash, schema_version, prompt_version, model),
                  FOREIGN KEY(meeting_id) REFERENCES meetings_truth(meeting_id)
                );
                """
            )

    # ---------- Truth (immutable) ----------

    def insert_meeting_truth(self, req: MeetingIngestRequest) -> MeetingRecord:
        created_at = _utc_now()
        transcript_hash = sha256_text(req.transcript)
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT meeting_id FROM meetings_truth WHERE meeting_id = ?",
                (req.meetingId,),
            ).fetchone()
            if existing:
                raise ValueError("meeting already exists (immutable truth record)")

            conn.execute(
                """
                INSERT INTO meetings_truth(
                  meeting_id, contact_id, type, occurred_at,
                  transcript, transcript_hash, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    req.meetingId,
                    req.contactId,
                    req.type,
                    req.occurredAt.astimezone(timezone.utc).isoformat(),
                    req.transcript,
                    transcript_hash,
                    created_at.isoformat(),
                ),
            )

        return MeetingRecord(
            meetingId=req.meetingId,
            contactId=req.contactId,
            type=req.type,
            occurredAt=req.occurredAt.astimezone(timezone.utc),
            transcript=req.transcript,
            transcriptHash=transcript_hash,
            createdAt=created_at,
        )

    def get_meeting_truth(self, meeting_id: str) -> Optional[MeetingRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM meetings_truth WHERE meeting_id = ?",
                (meeting_id,),
            ).fetchone()
            if not row:
                return None
            return _row_to_meeting(row)

    def list_contact_meetings_truth(self, contact_id: str) -> list[MeetingRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM meetings_truth
                WHERE contact_id = ?
                ORDER BY occurred_at DESC
                """,
                (contact_id,),
            ).fetchall()
            return [_row_to_meeting(r) for r in rows]

    # ---------- Derived ----------

    def upsert_analysis_derived(
        self,
        *,
        meeting: MeetingRecord,
        schema_version: str,
        prompt_version: str,
        model: str,
        derived: MeetingAnalysisData,
    ) -> MeetingAnalysisRecord:
        analyzed_at = _utc_now()
        with self._connect() as conn:
            # if exists, return existing (derived can be recomputed, but we keep deterministic cache by key)
            existing = conn.execute(
                """
                SELECT * FROM meeting_analysis_derived
                WHERE meeting_id = ?
                  AND transcript_hash = ?
                  AND schema_version = ?
                  AND prompt_version = ?
                  AND model = ?
                """,
                (meeting.meetingId, meeting.transcriptHash, schema_version, prompt_version, model),
            ).fetchone()
            if existing:
                return _row_to_analysis(existing)

            conn.execute(
                """
                INSERT INTO meeting_analysis_derived(
                  meeting_id, contact_id, transcript_hash, schema_version,
                  prompt_version, model, derived_json, analyzed_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meeting.meetingId,
                    meeting.contactId,
                    meeting.transcriptHash,
                    schema_version,
                    prompt_version,
                    model,
                    json.dumps(derived.model_dump(), ensure_ascii=False),
                    analyzed_at.isoformat(),
                ),
            )

        return MeetingAnalysisRecord(
            meetingId=meeting.meetingId,
            contactId=meeting.contactId,
            transcriptHash=meeting.transcriptHash,
            schemaVersion=schema_version,
            promptVersion=prompt_version,
            model=model,
            analyzedAt=analyzed_at,
            derived=derived,
        )

    def list_contact_analyses(self, contact_id: str) -> list[MeetingAnalysisRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM meeting_analysis_derived
                WHERE contact_id = ?
                ORDER BY analyzed_at DESC
                """,
                (contact_id,),
            ).fetchall()
            return [_row_to_analysis(r) for r in rows]


def _row_to_meeting(row: sqlite3.Row) -> MeetingRecord:
    occurred_at = datetime.fromisoformat(row["occurred_at"])
    created_at = datetime.fromisoformat(row["created_at"])
    return MeetingRecord(
        meetingId=row["meeting_id"],
        contactId=row["contact_id"],
        type=row["type"],
        occurredAt=occurred_at,
        transcript=row["transcript"],
        transcriptHash=row["transcript_hash"],
        createdAt=created_at,
    )


def _row_to_analysis(row: sqlite3.Row) -> MeetingAnalysisRecord:
    derived_dict: dict[str, Any] = json.loads(row["derived_json"])
    analyzed_at = datetime.fromisoformat(row["analyzed_at"])
    return MeetingAnalysisRecord(
        meetingId=row["meeting_id"],
        contactId=row["contact_id"],
        transcriptHash=row["transcript_hash"],
        schemaVersion=row["schema_version"],
        promptVersion=row["prompt_version"],
        model=row["model"],
        analyzedAt=analyzed_at,
        derived=MeetingAnalysisData.model_validate(derived_dict),
    )

