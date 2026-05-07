# DECISIONS — redact-ai

> Architecture Decision Log (ADL). Append-only record of significant
> design choices. Each entry follows a lightweight ADR format.

Entry template:

```text
## ADR-NNN — <Title>

- **Date:** YYYY-MM-DD
- **Status:** Proposed | Accepted | Superseded by ADR-XXX | Deprecated
- **Context:** What forces are at play?
- **Decision:** What did we choose?
- **Consequences:** Trade-offs and follow-ups.
```

---

## ADR-001 — Image-first as the primary input modality

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** Most existing PII tools focus on plain text. The most
  natural unit of "stuff users paste into AI tools" is a screenshot,
  and image-based redaction is materially harder than text.
- **Decision:** `redact-ai` treats images (screenshots, photos, scans)
  as the primary input. Text-only flows are a future convenience layer
  on top of the image pipeline, not a separate product.
- **Consequences:**
  - Requires an OCR + layout pipeline from day one.
  - Output fidelity (preserved layout, masked pixels) becomes a core
    correctness concern.
  - A pure-text mode can still emerge later as a thin adapter.

---

## ADR-002 — Local-first by default

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** A privacy tool that calls home contradicts itself.
  Users will not trust a redactor whose default sends their data
  somewhere.
- **Decision:** The default pipeline runs entirely on-device with no
  outbound network calls. Optional cloud-assisted detectors require
  explicit, per-invocation user consent.
- **Consequences:**
  - Constrains the choice of OCR engines and models.
  - Forces clear UX around any non-default cloud feature.
  - Simplifies the threat model.

---

## ADR-003 — Technology-agnostic core specification

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** The project is in a documentation phase. Locking in a
  language or framework prematurely would bias contributor onboarding
  and architectural choices.
- **Decision:** All v0.1 specs are written without prescribing a
  language, framework, or specific OCR engine. Concrete tech is chosen
  when a reference implementation begins.
- **Consequences:**
  - Slightly more abstract documents.
  - Multiple implementations remain viable.
  - Adapter contracts must be explicit.

---

## ADR-004 — Pipeline modularity (Ingest → OCR → Detect → Redact → Report)

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** Detection and redaction will evolve at different
  speeds. We want detectors to be replaceable without rewriting the
  redactor, and vice versa.
- **Decision:** Adopt a five-stage pipeline with explicit inter-stage
  contracts described in
  [`ARCHITECTURE_v0.1.md`](./ARCHITECTURE_v0.1.md).
- **Consequences:**
  - Higher up-front design cost.
  - Easier extensibility (new detectors, new redaction styles).
  - Clear boundaries for testing.

---

## ADR-005 — Fail closed on uncertainty

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** A redactor that emits partial output on failure is
  worse than no output, because it gives users a false sense of
  safety.
- **Decision:** On any failure that risks leaking sensitive content,
  `redact-ai` produces no output image and surfaces a clear error.
- **Consequences:**
  - Higher visible failure rate during development.
  - Stronger safety guarantees in production.

---

## ADR-006 — Manifest excludes raw matched text by default

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** The redaction manifest is a useful artefact for audit
  and review, but if it includes the raw matched values it becomes a
  secondary leak channel.
- **Decision:** Manifests include category, rule ID, location, and
  confidence — but **not** raw matched text. A `verbose_report` flag
  exists for power users who explicitly opt in.
- **Consequences:**
  - Default manifests are safe to share.
  - Verbose mode requires its own UX warnings.

---

## ADR-007 — v0.1 surface is a local web UI

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** [`UX_FLOW_v0.1.md`](./UX_FLOW_v0.1.md) and
  [`PRODUCT_v0.1.md`](./PRODUCT_v0.1.md) both left the v0.1 entry
  point open ("CLI, desktop, or both?"). Pure-Python ingestion of
  screenshots is OS-fragmented across clipboard, drag-drop, and
  share-sheet integrations, and a CLI alone excludes non-power-users
  from the most common moment ("I just took a screenshot — clean it
  before I paste it into ChatGPT"). A local web UI gives every user
  a familiar drag-and-drop canvas (the browser they already have
  open) without compromising the local-first principle.
- **Decision:** The v0.1 user-visible surface is a **local web UI** —
  a Python server bound to `127.0.0.1` plus a single static
  drag-and-drop HTML page served from the same process. The CLI is
  retained for power users and ships as a v0.2 surface (see
  [`ROADMAP.md`](./ROADMAP.md)).
- **Consequences:**
  - Adds a small, well-bounded HTTP attack surface that lives
    entirely on the loopback interface; hardening is captured in
    [`SECURITY_v0.1.md`](./SECURITY_v0.1.md).
  - HTTP roundtrip is included in the end-to-end latency budget
    (see [`NON_FUNCTIONAL_REQUIREMENTS_v0.1.md`](./NON_FUNCTIONAL_REQUIREMENTS_v0.1.md), NFR-1.1).
  - FastAPI (or an equivalent minimal Python web framework) joins
    the recommended MVP stack in
    [`TECH_STACK_OPTIONS_v0.1.md`](./TECH_STACK_OPTIONS_v0.1.md).
  - **Does not** revisit ADR-001 (image-first remains the v0.1 input
    modality) or ADR-002 (the localhost loopback is on-device; no
    user content crosses the network boundary).

---

> TODO: Future ADRs will be appended here as design choices are made.
