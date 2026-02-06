# Part 3 — Engineering Reasoning & Communication

## 1. Truth & Integrity

The design prevents manipulation and retroactive rewriting of outcomes by treating activity records as immutable. Meetings and transcripts are stored in an append-only truth store (e.g. `meetings_truth`); there is no update or delete of transcript content. If something must be corrected, we add a new record or event (e.g. a correction event) rather than overwriting. Derived data (LLM analysis, metrics) is stored separately and keyed by input hash and schema/prompt version, so it is always clear what source truth an insight came from. Access to write truth is restricted (e.g. operator-only for ingestion and analysis), and we can add an audit log that records who wrote what and when, so any change to the system is traceable.

## 2. AI Boundaries

The LLM is constrained in several ways to avoid hallucinated or misleading insights. 
1. Structured output only: the agent returns a fixed JSON schema (topics, objections, commitments, sentiment enum, outcome enum, summary) with no free-form narrative.
2. Validation: responses are parsed and validated with Pydantic; invalid or out-of-bounds values are rejected. 
3. Explicit derived label: analysis is stored as “derived” and never merged into the truth store, so the system never treats model output as factual record. 
4. Reproducibility: we store schema version, prompt version, model, and input hash so we can re-run or audit how an insight was produced. 
5. Bounded enums: sentiment and outcome are limited to a small set of values to avoid vague or invented categories.

## 3. Scalability

At 10× usage, the first bottlenecks are likely
1. SQLite and single-process backend: SQLite does not scale for concurrent writes and is not ideal for multi-instance deployment;
2. synchronous analysis: if every analyze request blocks on an LLM call, latency and rate limits will bite;
3. no caching: repeated analysis of the same transcript is recomputed. To scale, I would: move truth and derived storage to Postgres (or similar), add a job queue so analysis runs asynchronously and results are polled or pushed, cache analysis by (meetingId, transcriptHash, schemaVersion, model), and run the API behind multiple workers or as serverless functions with a shared database.

## 4. Public Results Layer

To anonymize and publish outcome metrics while limiting re-identification: (1) Aggregate only: publish counts, rates, or distributions over cohorts (e.g. by time window, segment), not per-contact or per-meeting rows. (2) Suppress small cells: do not publish aggregates where the underlying count is below a threshold (e.g. k-anonymity). (3) Limit dimensions: avoid cross-tabulations that combine many attributes (e.g. region × product × tenure) that could narrow to a single entity. (4) Pseudonymize and rotate: if any identifiers are needed in the pipeline, use one-way hashes or rotated salts so the same entity does not get the same public ID forever. (5) Review before publish: run checks (e.g. uniqueness of row counts, linkage attacks) before releasing a new metric or dashboard.
