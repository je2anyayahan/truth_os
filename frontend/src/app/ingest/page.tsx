"use client";

import { useState } from "react";
import Link from "next/link";
import { ingestMeeting, type IngestBody, type MeetingType } from "@/lib/api";

export default function IngestPage() {
  const [meetingId, setMeetingId] = useState("");
  const [contactId, setContactId] = useState("");
  const [type, setType] = useState<MeetingType>("sales");
  const [occurredAt, setOccurredAt] = useState(() =>
    new Date().toISOString().slice(0, 16)
  );
  const [transcript, setTranscript] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setMessage("");
    try {
      const body: IngestBody = {
        meetingId: meetingId.trim(),
        contactId: contactId.trim(),
        type,
        occurredAt: new Date(occurredAt).toISOString(),
        transcript: transcript.trim(),
      };
      await ingestMeeting(body);
      setStatus("success");
      setMessage("Meeting stored as immutable truth.");
      setMeetingId("");
      setContactId("");
      setTranscript("");
    } catch (err) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Request failed");
    }
  }

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: 24 }}>
      <nav style={{ marginBottom: 24 }}>
        <Link href="/">Home</Link>
        {" · "}
        <Link href="/ingest">Ingest</Link>
        {" · "}
        <Link href="/contacts">Contact intelligence</Link>
      </nav>
      <h1>Meeting ingestion</h1>
      <p style={{ color: "var(--foreground)", opacity: 0.8, marginBottom: 24 }}>
        Submit a meeting transcript. It is stored as immutable truth; analysis is derived separately.
      </p>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 16 }}>
          <label htmlFor="meetingId" style={{ display: "block", marginBottom: 4 }}>Meeting ID</label>
          <input
            id="meetingId"
            type="text"
            value={meetingId}
            onChange={(e) => setMeetingId(e.target.value)}
            required
            style={{ width: "100%", padding: 8 }}
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label htmlFor="contactId" style={{ display: "block", marginBottom: 4 }}>Contact ID</label>
          <input
            id="contactId"
            type="text"
            value={contactId}
            onChange={(e) => setContactId(e.target.value)}
            required
            style={{ width: "100%", padding: 8 }}
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label htmlFor="type" style={{ display: "block", marginBottom: 4 }}>Meeting type</label>
          <select
            id="type"
            value={type}
            onChange={(e) => setType(e.target.value as MeetingType)}
            style={{ width: "100%", padding: 8 }}
          >
            <option value="sales">sales</option>
            <option value="coaching">coaching</option>
          </select>
        </div>
        <div style={{ marginBottom: 16 }}>
          <label htmlFor="occurredAt" style={{ display: "block", marginBottom: 4 }}>Occurred at (ISO-8601)</label>
          <input
            id="occurredAt"
            type="datetime-local"
            value={occurredAt}
            onChange={(e) => setOccurredAt(e.target.value)}
            required
            style={{ width: "100%", padding: 8 }}
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label htmlFor="transcript" style={{ display: "block", marginBottom: 4 }}>Transcript</label>
          <textarea
            id="transcript"
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            required
            rows={6}
            style={{ width: "100%", padding: 8 }}
          />
        </div>
        <button type="submit" disabled={status === "loading"} style={{ padding: "10px 20px" }}>
          {status === "loading" ? "Submitting…" : "Submit"}
        </button>
      </form>
      {status === "success" && <p style={{ marginTop: 16, color: "green" }}>{message}</p>}
      {status === "error" && <p style={{ marginTop: 16, color: "crimson" }}>{message}</p>}
    </main>
  );
}
