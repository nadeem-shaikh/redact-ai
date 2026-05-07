# DATA FLOW — redact-ai (v0.1)

> Status: Draft. End-to-end view of how data moves through `redact-ai`,
> with explicit boundaries for sensitive content.

---

## 1. Trust Zones

```text
┌────────────────────────────────────────────────────────────┐
│                   USER DEVICE (Trusted)                    │
│                                                            │
│   ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │
│   │  Ingestor  │─▶│  Pipeline  │─▶│  Output (Redacted) │   │
│   └────────────┘  └────────────┘  └────────────────────┘   │
│           ▲                                ▲               │
│           │                                │               │
│       Raw input                       Redacted output      │
│       (sensitive)                     (de-identified)      │
└────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                ┌──────────────────────────────────────┐
                │    External AI Tool (Untrusted)      │
                │    (ChatGPT, Claude, etc.)           │
                └──────────────────────────────────────┘
```

Sensitive content **never** crosses the device boundary. The only
artefact that may leave the device is the **redacted** output the user
explicitly chooses to share.

---

## 2. Stage-by-Stage Flow

| # | Stage | Input | Output | Sensitive? |
| --- | --- | --- | --- | --- |
| 1 | Ingest | File / clipboard image | Normalised in-memory image | Yes |
| 2 | OCR | Normalised image | Document model (text + boxes) | Yes |
| 3 | Detect | Document model + policy | Findings list | Yes |
| 4 | Redact | Image + findings | Redacted image | Mixed* |
| 5 | Report | Findings (de-identified) | JSON manifest | No (default) |
| 6 | Persist | Redacted image + manifest | Files / streams | No |

\* The redacted image contains only non-sensitive pixels by design.

---

## 3. In-Memory Lifecycle

- All sensitive intermediate state lives in process memory only.
- The pipeline **MUST** zero buffers containing raw OCR text after the
  detector phase completes (best-effort).
- No intermediate stage writes to disk by default.

---

## 4. Persistence Rules

| Artefact | Persisted? | Where |
| --- | --- | --- |
| Raw input | No (unless user-supplied path) | n/a |
| Normalised image | No | Memory |
| OCR document model | No | Memory |
| Findings (raw text) | No | Memory |
| Redacted image | Yes (user-chosen path) | User filesystem |
| Manifest | Yes (user-chosen path) | User filesystem |
| Logs | Yes (no sensitive content) | User filesystem |

---

## 5. Network

- The default policy **MUST NOT** make any network calls during a
  redaction operation.
- Optional cloud-backed detectors (future) require explicit
  per-invocation user consent and **MUST** be feature-flagged.

See [`SECURITY_v0.1.md`](./SECURITY_v0.1.md).

---

## 6. Failure Paths

```text
              ┌────────────────────┐
Input ──────▶│   Pipeline starts   │
              └─────────┬──────────┘
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
   OCR fails       Detector fails    Redactor fails
        │               │                │
        ▼               ▼                ▼
  No output       Continue with     No output
  (fail closed)   remaining         (fail closed)
                  detectors;
                  log the error
```

---

## 7. Sequence Diagram (Logical)

```text
User              Ingestor   OCR        Detector    Redactor   Output
 │  drop image      │         │             │           │         │
 │ ───────────────▶ │         │             │           │         │
 │                  │ normalise            │           │         │
 │                  │ ──────▶ │             │           │         │
 │                  │         │ document    │           │         │
 │                  │         │ ──────────▶ │           │         │
 │                  │         │             │ findings  │         │
 │                  │         │             │ ────────▶ │         │
 │                  │         │             │           │ redacted│
 │                  │         │             │           │ ──────▶ │
 │  redacted image + report                            │         │
 │ ◀────────────────────────────────────────────────────────────  │
```

---

## 8. Open Questions

- Should we provide an explicit "memory pressure" mode for very large
  images? *(TODO)*
- How are batch flows represented (folder of screenshots)? *(TODO)*
