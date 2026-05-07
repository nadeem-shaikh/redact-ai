# PRODUCT — redact-ai (v0.1)

> Status: Draft. This document defines the product vision, target users,
> MVP scope, and high-level roadmap for `redact-ai`.

---

## 1. Vision

To make it **safe and effortless** for anyone to share images, screenshots,
and documents with AI tools, by automatically removing personally identifying
or sensitive content before it ever leaves the user's device.

> *"The privacy filter for the AI era."*

---

## 2. Mission

Eliminate accidental data exposure in AI workflows by providing a
**transparent, local-first redaction layer** that any user can drop into
their existing tools and habits.

---

## 3. Target Users

### Primary

- **Knowledge workers** who paste screenshots into ChatGPT/Claude for
  summarisation, translation, or analysis.
- **Healthcare professionals** redacting patient information from reports.
- **Finance and legal practitioners** sharing snippets of sensitive
  documents.
- **Software engineers** scrubbing logs, dashboards, or production data.

### Secondary

- **Journalists and researchers** handling source material.
- **Educators and students** sharing graded assignments or IDs.
- **Privacy-conscious individuals** sharing personal photos or letters.

---

## 4. User Pain Points

| Pain | Today's Workaround | Why It Fails |
| --- | --- | --- |
| Sensitive data leaks into AI tools | Manual cropping or skipping the tool | Slow, error-prone |
| Compliance teams block AI usage entirely | Shadow IT | Worse risk profile |
| Redacting screenshots manually | Black boxes in image editors | Tedious, easy to miss things |
| OCR-based redactors are text-only | Copy-paste workflows | Loses layout, breaks UX |

---

## 5. Product Principles

1. **Privacy by default.** No telemetry of user content. Local-first.
2. **Image-first.** Screenshots and photos are the primary input.
3. **Reversible only by the user.** Redactions in the output are permanent.
4. **Extensible.** New detectors and rules can be added without touching the core.
5. **Transparent.** Every redaction is explainable ("phone number, line 4").

---

## 6. MVP Scope (v0.1)

### In Scope

- Accept **screenshots and images** (`.png`, `.jpg`, `.jpeg`, `.webp`).
- Run **OCR** to extract text + bounding boxes.
- Detect a baseline set of sensitive entities (see
  [`REDACTION_RULES_v0.1.md`](./REDACTION_RULES_v0.1.md)).
- Produce a **redacted image** with sensitive regions visually masked.
- Provide a **detection report** summarising what was redacted and why.
- Operate **fully offline** for the default detector set.
- Ship a **local web UI** as the primary v0.1 entry surface — a
  Python server bound to `127.0.0.1` plus a single drag-and-drop page
  served from the same process. *(See ADR-007 in
  [`DECISIONS.md`](./DECISIONS.md).)* The CLI is a power-user surface
  in v0.2; see [`ROADMAP.md`](./ROADMAP.md).

### Out of Scope (for v0.1)

- Real-time browser/clipboard interception.
- Multi-page PDF support (planned for v0.2).
- Audio or video redaction.
- Cloud-hosted SaaS deployment.
- Reversible/un-redaction features.

---

## 7. Success Metrics

| Metric | Target (v0.1) |
| --- | --- |
| Recall on baseline PII set | ≥ 95% on the curated test corpus |
| False-positive rate | ≤ 5% on benign screenshots |
| End-to-end latency (1080p screenshot) | ≤ 3s on a modern laptop |
| Setup time for a new user | ≤ 2 minutes |

> TODO: Confirm measurement methodology in
> [`TEST_CASES_v0.1.md`](./TEST_CASES_v0.1.md).

---

## 8. High-Level Roadmap

| Version | Theme | Highlights |
| --- | --- | --- |
| v0.1 | Foundation | Documentation, MVP design, image redaction |
| v0.2 | Documents | Multi-page PDFs, layout-aware redaction |
| v0.3 | Integrations | Browser extension, clipboard helper |
| v0.4 | Custom rules | User-defined detectors and policies |
| v1.0 | Production | Hardened pipeline, signed releases, audit logs |

See [`ROADMAP.md`](./ROADMAP.md) for detail.

---

## 9. Open Questions

- What is the minimum acceptable accuracy bar before public release? *(TODO)*
- How do we communicate uncertainty to the user when a detection is low-confidence? *(TODO)*

> Resolved: "Should the MVP ship as a CLI, a desktop app, or both?" —
> the v0.1 surface is a **local web UI**, with the CLI deferred to
> v0.2. See ADR-007 in [`DECISIONS.md`](./DECISIONS.md).
