# UX FLOW — redact-ai (v0.1)

> Status: Draft. Step-by-step description of how a user interacts with
> `redact-ai`. Surface-agnostic; the same flow applies whether the
> entry point is a CLI, desktop app, or share-sheet integration.

---

## 1. Personas

- **Priya** — a doctor who needs to ask Claude about a complicated lab
  report without exposing patient identity.
- **Marcus** — a developer who pastes screenshots of dashboards into
  ChatGPT to debug analytics queries.
- **Lena** — a journalist redacting source documents before sharing
  them with an AI summariser.

---

## 2. Top-Level Flow

```text
1. Capture / select input
2. Choose policy (or accept default)
3. Run redaction
4. Review result
5. Share with AI tool
```

---

## 3. Step-by-Step Walkthrough

### Step 1 — Capture / Select Input

- User has an image: a screenshot, a phone photo, or a scanned page.
- Entry points:
  - **Local web UI (primary v0.1 surface).** The user runs
    `redact-ai`, which starts a local server bound to `127.0.0.1`
    and opens a single page in the user's default browser. The user
    drops the image onto the page (or uses the file picker).
  - *(v0.2)* CLI: `redact-ai run --input path/to/image.png` — for
    power users and scripted flows.
  - *(later)* OS share-sheet integration *(see ROADMAP.md)*.

**Acceptance:**

- The system confirms the file format is supported.
- An unsupported format produces a clear error with a suggested fix.
- The local web UI is reachable only from the loopback interface.

### Step 2 — Choose Policy

- The user accepts the default policy or chooses an alternate.
- The default policy enables the baseline rule set from
  [`REDACTION_RULES_v0.1.md`](./REDACTION_RULES_v0.1.md).
- Options like "strict" or "lenient" are presented, with plain-language
  descriptions ("safer, may over-redact" / "lighter touch").

**Acceptance:**

- A first-time user can complete this step without reading documentation.

### Step 3 — Run Redaction

- The user triggers the operation.
- A progress indicator shows the current pipeline stage.
- The operation completes within the latency target (`NFR-1.1`).

**Acceptance:**

- Progress feedback is visible for any operation longer than ~1 second.

### Step 4 — Review Result

- The user is shown:
  - The redacted image.
  - A summary: counts per category and a list of redaction styles used.
  - Any warnings (e.g. low-confidence regions, photo regions not
    handled).
- The user can re-run with a different policy if they disagree with
  the result.

**Acceptance:**

- The user can answer "what was redacted, and why?" from the summary.
- The summary never reveals raw matched text by default.

### Step 5 — Share With AI Tool

- The user copies, drags, or saves the redacted output.
- The AI tool receives only the de-identified artefact.

**Acceptance:**

- No part of the workflow tempts the user to share the original by
  mistake (e.g. the redacted file has a clearly distinct filename).

---

## 4. Edge-Case Flows

### 4.1 No detections found

- The user is told explicitly that no sensitive content was found.
- The output is still produced (a copy of the input).

### 4.2 Low-confidence detections

- The system surfaces a "Review carefully" badge.
- Optional: highlight the low-confidence regions in the review screen.

### 4.3 Detector failure

- One detector failing does not abort the whole operation.
- The summary reports which detectors did not run and why.

### 4.4 Catastrophic failure

- The system fails closed: no output image is produced.
- The user sees a clear error and a one-line remediation hint.

---

## 5. Notifications & Copy

- All copy uses **plain language**, never marketing terms.
- Avoid "AI", "ML", "NLP" jargon in the user-facing UI.
- Frame messages around **the user's intent** ("ready to share with AI"),
  not the system's internals.

---

## 6. Open Questions

- Should the review step include an editable preview to add/remove
  redactions manually? *(TODO)*
- How do we onboard users to non-default policies? *(TODO)*

> Resolved: "What is the v0.1 entry point — CLI, desktop, or both?"
> — the v0.1 surface is a **local web UI**; the CLI is a v0.2
> power-user surface. See ADR-007 in
> [`DECISIONS.md`](./DECISIONS.md).
