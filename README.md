# truthOS — Meeting Intelligence

Ingest meeting transcripts, store them as immutable records, run LLM analysis, and view contact-level insights in a web UI. This repo has a Python backend (FastAPI), a Next.js frontend (App Router, TypeScript), and design/reasoning docs in `docs/`.

Analysis uses a real LLM (Groq or OpenAI). You need an API key to run analysis; there’s no mock. Groq has a free tier and is the default.

---

## Setup instructions

Get an API key first. Use either Groq (free at console.groq.com) or OpenAI (platform.openai.com). Create a `.env` file in the repo root (same folder as `api/`) with one of these:

Groq:

```
GROQ_API_KEY=gsk_your-key-here
GROQ_MODEL=llama-3.3-70b-versatile
```

OpenAI:

```
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

If you set both, Groq is used. Restart the backend after editing `.env`.

Backend: from repo root, create a venv in `api/`, install deps, then run uvicorn from the root so the app can find the `api` package:

```bash
cd api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd ..
python -m uvicorn api.index:app --reload --host 0.0.0.0 --port 8000
```

The API runs at http://localhost:8000. It has three routes: POST /api/meetings (ingest), POST /api/meetings/{meetingId}/analyze (run LLM analysis), GET /api/contacts/{contactId}/meetings (list meetings and analyses). The frontend sends a header `x-user-role: operator`; analysis is only allowed for that role.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. You can set `NEXT_PUBLIC_API_URL` in `.env.local` if the API is on a different URL; it defaults to http://localhost:8000. The app has a meeting ingestion form at /ingest and a contact intelligence view at /contacts where you can expand meetings and run LLM analysis (needs the API key from above).

Tests: from repo root run `python -m pytest api/tests -v`. For the frontend, `cd frontend && npm test`.

Deployment: deploy the frontend folder to Vercel (or point your build at it). The backend can go to Vercel as Python serverless or to something like Railway/Render. Add GROQ_API_KEY or OPENAI_API_KEY to the backend env so analysis works in production.

---

## Architecture overview

Meetings and transcripts are stored as immutable truth: once written, they aren’t updated. LLM output (topics, objections, commitments, sentiment, outcome, summary) is stored in a separate “derived” table so we never treat model output as source of truth. Everything is keyed by contactId so the UI can load all meetings and analyses for a contact. Flow: ingest writes to the truth store, analyze calls the LLM and writes to the derived store, and the UI shows raw record and derived insights in separate sections.

---

## AI usage explanation

We use a single-purpose analysis agent: it takes a transcript and returns structured JSON only (no chat). Input is the raw transcript. Output is a fixed shape: topics, objections, commitments, sentiment (one of a small set of values), outcome (same), and a summary string. The response is validated with Pydantic and stored as derived data. We store schema and prompt version so we can reproduce or re-run. Sentiment and outcome are limited to enums to keep the model from inventing categories. We use JSON mode where the provider supports it.

---

## Assumptions and limitations

Auth is simplified: the app uses a header for role (operator vs basic). There’s no real login. Storage is SQLite for ease of setup; on Vercel serverless the filesystem is ephemeral unless you plug in an external DB. The slice is single-tenant with no org scoping. The public results layer and time-series baselines from the design doc are out of scope here. You need a Groq or OpenAI key to use analysis; the project is set up to show real LLM integration, not a mock.
