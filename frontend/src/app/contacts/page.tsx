"use client";

import { useState } from "react";
import Link from "next/link";
import { fetchContactMeetings, analyzeMeeting, type ContactMeetingsResponse, type MeetingRecord, type AnalysisRecord } from "@/lib/api";

function MeetingRow({
  meeting,
  analysis,
  onAnalyzed,
}: {
  meeting: MeetingRecord;
  analysis?: AnalysisRecord;
  onAnalyzed?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const isAnalysisForThis = analysis?.meetingId === meeting.meetingId;

  async function handleAnalyze() {
    setAnalyzing(true);
    try {
      await analyzeMeeting(meeting.meetingId);
      onAnalyzed?.();
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div style={{ border: "1px solid #ccc", borderRadius: 8, marginBottom: 12, overflow: "hidden" }}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%",
          padding: 16,
          textAlign: "left",
          background: "var(--background)",
          border: "none",
          cursor: "pointer",
          fontWeight: 600,
        }}
      >
        {meeting.meetingId} — {meeting.type} — {new Date(meeting.occurredAt).toLocaleString()}
        {isAnalysisForThis ? " (has analysis)" : ""}
      </button>
      {!isAnalysisForThis && (
        <div style={{ padding: "8px 16px", borderTop: "1px solid #eee" }}>
          <button type="button" onClick={handleAnalyze} disabled={analyzing} style={{ padding: "6px 12px" }}>
            {analyzing ? "Analyzing…" : "Run LLM analysis"}
          </button>
        </div>
      )}
      {open && (
        <div style={{ padding: 16, borderTop: "1px solid #ccc", background: "var(--background)" }}>
          <section style={{ marginBottom: 16 }}>
            <h4 style={{ marginBottom: 8 }}>Raw record (immutable truth)</h4>
            <p style={{ fontSize: 14, opacity: 0.9 }}>
              Meeting ID: {meeting.meetingId} · Contact: {meeting.contactId} · Created: {new Date(meeting.createdAt).toISOString()}
            </p>
            <p style={{ whiteSpace: "pre-wrap", marginTop: 8, fontSize: 14 }}>
              {meeting.transcript.slice(0, 500)}
              {meeting.transcript.length > 500 ? "…" : ""}
            </p>
            <p style={{ fontSize: 12, opacity: 0.7 }}>Hash: {meeting.transcriptHash}</p>
          </section>
          {isAnalysisForThis && analysis && (
            <section>
              <h4 style={{ marginBottom: 8 }}>Derived insights (LLM analysis)</h4>
              <p style={{ fontSize: 12, opacity: 0.8 }}>
                Model: {analysis.model} · Schema: {analysis.schemaVersion} · Analyzed: {new Date(analysis.analyzedAt).toISOString()}
              </p>
              <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                <li>Topics: {analysis.derived.topics.join(", ") || "—"}</li>
                <li>Objections: {analysis.derived.objections.join(", ") || "—"}</li>
                <li>Commitments: {analysis.derived.commitments.join(", ") || "—"}</li>
                <li>Sentiment: {analysis.derived.sentiment}</li>
                <li>Outcome: {analysis.derived.outcome}</li>
              </ul>
              <p style={{ marginTop: 8 }}>{analysis.derived.summary}</p>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

export default function ContactsPage() {
  const [contactId, setContactId] = useState("");
  const [data, setData] = useState<ContactMeetingsResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState("");

  async function loadContact() {
    if (!contactId.trim()) return;
    setStatus("loading");
    setError("");
    setData(null);
    try {
      const res = await fetchContactMeetings(contactId.trim());
      setData(res);
      setStatus("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch");
      setStatus("error");
    }
  }

  function handleFetch(e: React.FormEvent) {
    e.preventDefault();
    loadContact();
  }

  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: 24 }}>
      <nav style={{ marginBottom: 24 }}>
        <Link href="/">Home</Link>
        {" · "}
        <Link href="/ingest">Ingest</Link>
        {" · "}
        <Link href="/contacts">Contact intelligence</Link>
      </nav>
      <h1>Contact intelligence</h1>
      <p style={{ color: "var(--foreground)", opacity: 0.8, marginBottom: 24 }}>
        View meetings and analysis for a contact. Raw records and derived insights are shown separately.
      </p>
      <form onSubmit={handleFetch} style={{ marginBottom: 24 }}>
        <label htmlFor="contactId" style={{ display: "block", marginBottom: 4 }}>Contact ID</label>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input
            id="contactId"
            type="text"
            value={contactId}
            onChange={(e) => setContactId(e.target.value)}
            placeholder="e.g. c_1"
            style={{ flex: 1, minWidth: 120, padding: 8 }}
          />
          <button type="submit" disabled={status === "loading"}>
            {status === "loading" ? "Loading…" : "Fetch meetings"}
          </button>
        </div>
      </form>
      {error && <p style={{ color: "crimson", marginBottom: 16 }}>{error}</p>}
      {data && (
        <div>
          <h2>Meetings for {data.contactId}</h2>
          {data.meetings.length === 0 ? (
            <p>No meetings found.</p>
          ) : (
            data.meetings.map((m) => (
              <MeetingRow
                key={m.meetingId}
                meeting={m}
                analysis={data.analyses.find((a) => a.meetingId === m.meetingId)}
                onAnalyzed={loadContact}
              />
            ))
          )}
        </div>
      )}
    </main>
  );
}
