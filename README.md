# redact-ai

**Redact before you prompt.**

A privacy-first preprocessing layer that detects and masks sensitive
information in **images, screenshots, and documents** before they are
sent to ChatGPT, Claude, Gemini, or any other LLM.

> Status: **v0.1 MVP.** Local web UI runs on `127.0.0.1` and never
> calls the network. See [ADR-007](./docs/DECISIONS.md) for the surface
> decision and [ADR-002](./docs/DECISIONS.md) for the local-first
> guarantee.

## Quick start

1. **Install Tesseract 5+** for your platform
   (`brew install tesseract`, `apt-get install tesseract-ocr`, or
   `choco install tesseract`). Python 3.11 or 3.12 required.
2. **Clone, build, and run from source** — the spaCy NER model used
   by ID-006 is pulled automatically as a dependency (see
   [ADR-011](./docs/DECISIONS.md); adds ~50 MB):
   ```bash
   git clone https://github.com/nadeem-shaikh/redact-ai.git
   cd redact-ai
   uv sync --extra dev              # build: install runtime + dev deps
   uv run redact-ai                 # run: opens http://127.0.0.1:<port>
   ```
3. **Drop a screenshot** onto the page. The redacted image plus a
   summary appears in the same window.
4. **Click "Download redacted image"** to save the safe copy; click
   **"Download manifest"** for the JSON audit trail.

Everything runs on your device. No telemetry, no outbound calls.

---

## The Problem

People paste sensitive content into LLMs every day:

- Bank statements, invoices, tax forms
- Medical reports and lab results
- Government IDs, passports, driver's licences
- Private chat and email screenshots
- Internal company documents

This is a fast-growing problem:

- **LLM adoption is outpacing data-handling literacy.** Most users
  don't realise screenshots carry account numbers, names, MRNs.
- **Once a token is sent, it's gone.** No undo. No retention guarantee
  from third-party model providers.
- **Compliance regimes are tightening** (GDPR, HIPAA, SOC 2),
  but tooling has not caught up.

Existing tools fall short:

- Most PII tools are **text-only** and require structured input.
- Image editors require **manual cropping or black-boxing** — slow
  and easy to miss things.
- DLP platforms target enterprises, not the user with a screenshot
  in their clipboard.

---

## The Solution

`redact-ai` is a deterministic safety layer that sits between the
user and any AI tool.

```text
Input  →  OCR  →  Detection  →  Redaction  →  Safe Output  →  AI Tool
```

It accepts an image, recognises text + layout, identifies sensitive
entities, masks the corresponding pixels, and emits a redacted image
plus a structured manifest of what was changed and why.

---

## Example

**Before** — original screenshot of a bank statement:

```text
┌────────────────────────────────────────────────────────────┐
│  ACME BANK — Statement                                     │
│                                                            │
│  Aanya Sharma                                              │
│  221B Baker Street, NW1 6XE                                │
│  IBAN: GB29 NWBK 6016 1331 9268 19                         │
│                                                            │
│  Transactions                                              │
│   2026-04-12  Salary credit         +£3,200.00             │
│   2026-04-15  Grocery — Tesco          -£42.18             │
│   2026-04-18  Transfer to savings    -£500.00              │
└────────────────────────────────────────────────────────────┘
```

**After** — same screenshot, processed by `redact-ai`:

```text
┌────────────────────────────────────────────────────────────┐
│  ACME BANK — Statement                                     │
│                                                            │
│  ███████████                                               │
│  █████████████████████████████                             │
│  IBAN: ████████████████████████                            │
│                                                            │
│  Transactions                                              │
│   2026-04-12  Salary credit         +£3,200.00             │
│   2026-04-15  Grocery — Tesco          -£42.18             │
│   2026-04-18  Transfer to savings    -£500.00              │
└────────────────────────────────────────────────────────────┘
```

Manifest (JSON):

```json
{
  "stats": { "redactions_total": 3,
             "by_category": { "IDENTITY": 1, "CONTACT": 1, "FINANCIAL": 1 } },
  "findings": [
    { "rule_id": "ID-001", "category": "IDENTITY",  "confidence": "high" },
    { "rule_id": "CO-003", "category": "CONTACT",   "confidence": "high" },
    { "rule_id": "FI-002", "category": "FINANCIAL", "confidence": "high" }
  ]
}
```

> Manifests never include the raw matched text by default. See
> [ADR-006](./docs/DECISIONS.md).

---

## Architecture

```text
┌────────────────────────────────────────────────────────────────────┐
│                           USER DEVICE                              │
│                                                                    │
│  ┌──────────────┐    ┌──────────────┐                              │
│  │  Browser     │───▶│  Local web   │  (FastAPI on 127.0.0.1)      │
│  │  drag-drop   │    │  server      │                              │
│  └──────────────┘    └──────┬───────┘                              │
│                             │                                      │
│                             ▼                                      │
│       ┌────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐      │
│       │Ingestor│──▶│OCR/Layout│──▶│ Detector │──▶│ Redactor │      │
│       └────────┘   └──────────┘   └──────────┘   └────┬─────┘      │
│                                                       │            │
│                          Redacted image + manifest ◀──┘            │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                       External AI tool (untrusted)
```

| Stage | Responsibility |
| --- | --- |
| **Ingestor** | Validate format; strip EXIF; canonical in-memory image. |
| **OCR / Layout** | Recognise text + bounding boxes; preserve reading order. |
| **Detector** | Apply pluggable detectors (regex, dictionary, ML); emit findings with categories and confidence. |
| **Redactor** | Mask each finding with the policy's redaction style; produce safe output + manifest. |

Pipeline contracts are defined in
[`docs/ARCHITECTURE_v0.1.md`](./docs/ARCHITECTURE_v0.1.md) and
[`docs/API_SPEC_v0.1.md`](./docs/API_SPEC_v0.1.md). Sensitive content
**never** leaves the device — see
[`docs/DATA_FLOW_v0.1.md`](./docs/DATA_FLOW_v0.1.md).

---

## Why This Is Hard

- **OCR noise.** Real screenshots come with anti-aliasing, low DPI,
  and unusual fonts. A wrong character breaks regex matches.
- **Layout understanding.** A name and a street can sit in different
  blocks; a card number can wrap across lines. Detection has to be
  aware of structure, not just substrings.
- **False positives vs false negatives.** A missed PAN is a privacy
  failure; a redacted invoice number is a UX failure. We bias toward
  recall, but every choice has a cost.
- **Partial entities.** Half of a phone number, the last 4 of an ID,
  a redacted DOB next to a full name. The system needs to reason
  about *combinations*, not isolated tokens.
- **Multi-language and multi-script.** Identifiers, addresses, and
  honorifics differ across locales; many real screenshots are bilingual.
- **Readability after redaction.** A mask that swallows entire
  paragraphs is safe but useless. The output must remain useful for
  the user's downstream prompt.

---

## Design Principles

1. **Privacy first.** No telemetry of user content. Ever.
2. **Local-first by default.** The default pipeline runs entirely
   on-device. The localhost loopback is on-device.
3. **Modular architecture.** Ingestor → OCR → Detector → Redactor
   are independently replaceable behind explicit contracts.
4. **Deterministic safety layer.** The same input + the same policy
   produces the same redacted output and an equivalent manifest.
5. **AI-agent friendly.** Stable IDs (`FR-x.y`, `ADR-NNN`,
   `CO-002`), explicit contracts, and per-doc open-question lists
   make this codebase easy for AI coding agents to extend without
   ambiguity.

---

## Roadmap

| Version | Theme | Highlights |
| --- | --- | --- |
| **v0.1** | Foundation + image MVP | Local web UI, baseline detectors, solid-block redactor, manifest |
| **v0.2** | Power-user surfaces | CLI, clipboard ingestion, folder watcher, more redaction styles |
| **v0.3** | Documents | Multi-page PDFs, layout-aware redaction (tables, forms) |
| **v0.4** | Integrations | Browser extension, OS share-sheet, desktop app shell |
| **v0.5** | Custom rules | User-defined detectors, policy authoring tooling |
| **v1.0** | Production | Reproducible builds, signed binaries, public benchmark, security review |

Full roadmap: [`docs/ROADMAP.md`](./docs/ROADMAP.md).

---

## Evaluation

We measure four things:

| Metric | What it captures | Target (v0.1) |
| --- | --- | --- |
| **Precision / Recall** | Detection quality on a curated PII corpus | Recall ≥ 95%, FP rate ≤ 5% |
| **OCR robustness** | Accuracy across DPI, lighting, compression | TBD baseline |
| **Redaction completeness** | No sensitive pixels remain in masked regions | 100% on golden set |
| **Latency** | End-to-end time including localhost roundtrip | ≤ 3 s for 1080p screenshots |
| **Readability retention** | Non-sensitive content survives intact | Qualitative + diff-based |

### Reference datasets

The curated test corpus targets realistic, **synthetic** examples:

- Invoices and bank statements
- Government ID cards
- Medical lab reports
- Chat / email screenshots
- Multi-language receipts
- Code editor screenshots with credentials

Test cases and acceptance criteria: [`docs/TEST_CASES_v0.1.md`](./docs/TEST_CASES_v0.1.md).

---

## Threat Model

**Assumptions about the user**

- The user is acting in good faith and wants to share an artefact
  with an AI tool *without* leaking sensitive content.
- The user controls their device. We do not defend against an
  adversary with root.

**Trust boundaries**

- **Trusted:** the user's process, memory, the localhost loopback,
  user-chosen output paths.
- **Untrusted:** the network, the downstream AI tool, third-party
  services, ad-hoc cloud detectors.

**Goal**

> No sensitive content leaves the system unredacted.

The pipeline **fails closed**: on any error that risks leaking
sensitive data, no output is produced.

Full threat model and risk register:
[`docs/SECURITY_v0.1.md`](./docs/SECURITY_v0.1.md).

---

## Documentation

| Document | Purpose |
| --- | --- |
| [PRODUCT_v0.1.md](./docs/PRODUCT_v0.1.md) | Vision, users, MVP scope |
| [ARCHITECTURE_v0.1.md](./docs/ARCHITECTURE_v0.1.md) | High-level system design |
| [FUNCTIONAL_REQUIREMENTS_v0.1.md](./docs/FUNCTIONAL_REQUIREMENTS_v0.1.md) | What the system must do |
| [NON_FUNCTIONAL_REQUIREMENTS_v0.1.md](./docs/NON_FUNCTIONAL_REQUIREMENTS_v0.1.md) | Quality attributes |
| [REDACTION_RULES_v0.1.md](./docs/REDACTION_RULES_v0.1.md) | What counts as sensitive |
| [OCR_PIPELINE_v0.1.md](./docs/OCR_PIPELINE_v0.1.md) | Image → text pipeline |
| [DATA_FLOW_v0.1.md](./docs/DATA_FLOW_v0.1.md) | Trust zones and data movement |
| [API_SPEC_v0.1.md](./docs/API_SPEC_v0.1.md) | Public interface contract |
| [SECURITY_v0.1.md](./docs/SECURITY_v0.1.md) | Privacy and threat model |
| [TEST_CASES_v0.1.md](./docs/TEST_CASES_v0.1.md) | Realistic example inputs/outputs |
| [UX_FLOW_v0.1.md](./docs/UX_FLOW_v0.1.md) | Step-by-step user interactions |
| [TECH_STACK_OPTIONS_v0.1.md](./docs/TECH_STACK_OPTIONS_v0.1.md) | Stack comparison + recommendation |
| [TECHNICAL_DESIGN_v0.1.md](./docs/TECHNICAL_DESIGN_v0.1.md) | MVP implementation blueprint (TDD) |
| [MVP_BUILD_SPEC_v0.1.md](./docs/MVP_BUILD_SPEC_v0.1.md) | Agent-executable build brief (milestones, gates, do-nots) |
| [BUILD_SPEC_v0.1.md](./docs/BUILD_SPEC_v0.1.md) | Implementation spec: layout, deps, schemas, build/run |
| [DETECTORS_v0.1.md](./docs/DETECTORS_v0.1.md) | Per-rule regex / heuristic specifications |
| [DECISIONS.md](./docs/DECISIONS.md) | Architecture Decision Log (ADR) |
| [ROADMAP.md](./docs/ROADMAP.md) | Milestones and release plan |
| [CONTRIBUTING.md](./docs/CONTRIBUTING.md) | How to contribute |

---

## Contributing

We welcome contributors of all kinds — engineers, designers, security
researchers, and writers. Start with
[`docs/CONTRIBUTING.md`](./docs/CONTRIBUTING.md). Issues and proposals
should reference the relevant document IDs (`FR-x.y`, `ADR-NNN`,
`CO-002`, etc.) so discussions stay precise.

---

## License

[MIT](./LICENSE).
