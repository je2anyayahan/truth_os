import Link from "next/link";

export default function Home() {
  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: 48 }}>
      <h1>truthOS — Meeting intelligence</h1>
      <p style={{ marginTop: 8, opacity: 0.9 }}>
        Ingest meeting transcripts and view contact-level insights. Raw records (truth) and LLM-derived analysis are kept separate.
      </p>
      <ul style={{ marginTop: 32, listStyle: "none", padding: 0 }}>
        <li style={{ marginBottom: 16 }}>
          <Link href="/ingest" style={{ fontSize: 18, textDecoration: "underline" }}>
            Meeting ingestion
          </Link>
          <span style={{ display: "block", marginTop: 4, opacity: 0.8 }}>
            Submit a transcript (meeting ID, contact ID, type, timestamp).
          </span>
        </li>
        <li>
          <Link href="/contacts" style={{ fontSize: 18, textDecoration: "underline" }}>
            Contact intelligence
          </Link>
          <span style={{ display: "block", marginTop: 4, opacity: 0.8 }}>
            List meetings for a contact with transcript preview and analysis.
          </span>
        </li>
      </ul>
    </main>
  );
}
