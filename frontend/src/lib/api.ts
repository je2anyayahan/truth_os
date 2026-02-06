const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DEFAULT_HEADERS: HeadersInit = {
  "Content-Type": "application/json",
  "x-user-role": "operator",
  "x-user-id": "demo-user",
};

export type MeetingType = "sales" | "coaching";

export interface IngestBody {
  meetingId: string;
  contactId: string;
  type: MeetingType;
  occurredAt: string; // ISO-8601
  transcript: string;
}

export interface MeetingRecord {
  meetingId: string;
  contactId: string;
  type: MeetingType;
  occurredAt: string;
  transcript: string;
  transcriptHash: string;
  createdAt: string;
}

export interface AnalysisDerived {
  topics: string[];
  objections: string[];
  commitments: string[];
  sentiment: string;
  outcome: string;
  summary: string;
}

export interface AnalysisRecord {
  meetingId: string;
  contactId: string;
  transcriptHash: string;
  schemaVersion: string;
  promptVersion: string;
  model: string;
  analyzedAt: string;
  derived: AnalysisDerived;
}

export interface ContactMeetingsResponse {
  contactId: string;
  meetings: MeetingRecord[];
  analyses: AnalysisRecord[];
}

export async function ingestMeeting(body: IngestBody): Promise<{ truth: MeetingRecord; derived: null; note: string }> {
  const r = await fetch(`${API_BASE}/api/meetings`, {
    method: "POST",
    headers: DEFAULT_HEADERS,
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail));
  }
  return r.json();
}

export async function analyzeMeeting(meetingId: string): Promise<{
  truth_ref: { meetingId: string; contactId: string; transcriptHash: string };
  analysis: AnalysisRecord;
  note: string;
}> {
  const r = await fetch(`${API_BASE}/api/meetings/${encodeURIComponent(meetingId)}/analyze`, {
    method: "POST",
    headers: DEFAULT_HEADERS,
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail));
  }
  return r.json();
}

export async function fetchContactMeetings(contactId: string): Promise<ContactMeetingsResponse> {
  const r = await fetch(`${API_BASE}/api/contacts/${encodeURIComponent(contactId)}/meetings`, {
    headers: DEFAULT_HEADERS,
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail));
  }
  return r.json();
}
