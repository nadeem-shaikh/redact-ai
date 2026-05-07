# ARCHITECTURE — redact-ai (v0.1)

> Status: Draft. Technology-agnostic high-level architecture for the
> image-first redaction pipeline.

---

## 1. Goals

- **Modularity.** Each stage of the pipeline is replaceable.
- **Locality.** All processing can run on the user's device.
- **Determinism.** The same input + the same policy produces the same
  redacted output.
- **Auditability.** Every redaction is traceable to a rule and a region.

---

## 2. System Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                            redact-ai                                 │
│                                                                      │
│   ┌────────────┐   ┌─────────────┐   ┌────────────┐   ┌───────────┐  │
│   │  Ingestor  │──▶│    OCR &    │──▶│  Detector  │──▶│ Redactor  │  │
│   │            │   │   Layout    │   │   Engine   │   │           │  │
│   └────────────┘   └─────────────┘   └────────────┘   └───────────┘  │
│         │                 │                 │              │         │
│         ▼                 ▼                 ▼              ▼         │
│     Raw Image        Text + Boxes      Findings        Redacted     │
│                                       (entity, box,    Image +      │
│                                        confidence)     Report       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Components

### 3.0 Surfaces (v0.1)

`redact-ai` exposes one user-visible surface in v0.1: a **local web
UI** — a Python server bound to `127.0.0.1` plus a single static
drag-and-drop page served from the same process. The surface sits in
front of the pipeline below; the pipeline itself is unchanged.

```text
Browser (localhost:<port>)
        │  drag-drop image
        ▼
HTTP server (127.0.0.1)  ──▶  Ingestor → OCR → Detector → Redactor → Report
        ▲                                                             │
        └─────────────── redacted image + manifest ◀───────────────────┘
```

The CLI is a v0.2 power-user surface (see
[`ROADMAP.md`](./ROADMAP.md)). Both surfaces call the same pipeline
via the contracts in [`API_SPEC_v0.1.md`](./API_SPEC_v0.1.md).

### 3.1 Ingestor

- Accepts an input artifact: image file, screenshot, or document page.
- Normalises format, colour space, and resolution.
- Emits a canonical in-memory representation.
- Responsible for: format validation, EXIF stripping, sanitisation.

### 3.2 OCR & Layout

- Extracts text content **and** spatial layout (bounding boxes, lines,
  blocks, reading order).
- Output is a structured document model — independent of any specific
  OCR engine.
- See [`OCR_PIPELINE_v0.1.md`](./OCR_PIPELINE_v0.1.md).

### 3.3 Detector Engine

- Applies a configurable set of **detectors** to the document model.
- Each detector consumes text + layout and returns `Findings`:
  `{ entity_type, bounding_box, confidence, source_rule }`.
- Detectors are pluggable: regex, dictionary, ML-based, or hybrid.
- See [`REDACTION_RULES_v0.1.md`](./REDACTION_RULES_v0.1.md).

### 3.4 Redactor

- Consumes the original image plus the merged set of findings.
- Applies a **redaction style** (solid block, blur, pixelate, label).
- Produces:
  - A redacted image (binary identical for identical input + policy).
  - A structured **redaction report** describing each action taken.

### 3.5 Reporting

- Human-readable summary (counts per category).
- Machine-readable manifest (JSON, format defined in
  [`API_SPEC_v0.1.md`](./API_SPEC_v0.1.md)).

---

## 4. Data Movement

A high-level data-flow diagram lives in
[`DATA_FLOW_v0.1.md`](./DATA_FLOW_v0.1.md). Key invariants:

- Raw user content never crosses a process boundary except for the
  redactor's output stage.
- No component writes user content to disk by default.
- The detection report contains **categories and counts**, never raw
  matched values.

---

## 5. Extensibility Points

| Extension Point | Purpose | Examples |
| --- | --- | --- |
| OCR adapter | Plug a different OCR engine | Tesseract, PaddleOCR, vendor APIs |
| Detector | Identify a new entity type | "Patient ID", "Internal ticket number" |
| Redaction style | Visual treatment | Block, blur, pixelate, glyph-replace |
| Output sink | Where the result goes | Filesystem, clipboard, share-sheet |

---

## 6. Configuration Model

- A **policy** is a named bundle of: enabled detectors, thresholds, and
  redaction styles.
- Policies are versioned and human-readable.
- Default policies ship with the project; users can author custom ones.

> TODO: Define the policy schema in `API_SPEC_v0.1.md`.

---

## 7. Non-Functional Considerations

See [`NON_FUNCTIONAL_REQUIREMENTS_v0.1.md`](./NON_FUNCTIONAL_REQUIREMENTS_v0.1.md)
for performance, reliability, and security targets.

---

## 8. Out of Scope (v0.1)

- Distributed or server-side execution.
- Realtime/streaming inputs.
- Reversible redaction.

---

## 9. Open Questions

- Should detection and redaction live in separate processes for hardening? *(TODO)*
- How do we represent multi-page documents in the canonical model? *(TODO)*
- Should the policy engine support conditional rules (e.g. "only redact
  IDs if a name is also present")? *(TODO)*
