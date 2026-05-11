# Prompts

This file records the verbatim prompts used to scaffold and evolve this
repository with an AI coding agent. Keeping the prompts alongside the
code makes the project's documentation-first development process
reproducible and auditable.

---

## Prompt 1 — Initial repository scaffold

Create a clean, documentation-first repository structure for an open-source project named `redact-ai`.

Project Summary:
redact-ai is a privacy-first tool that detects and redacts sensitive personal information from screenshots, images, and documents before they are shared with AI systems like ChatGPT or Claude.

The repository should be focused on:
- product clarity
- architecture planning
- AI-assisted development
- maintainability
- extensibility

Do NOT assume any programming language or framework yet.

The goal is to establish a strong documentation foundation before implementation begins.

Generate the following repository structure exactly:

redact-ai/
├── README.md
├── LICENSE
├── .gitignore
│
├── docs/
│   ├── PRODUCT_v0.1.md
│   ├── IDEA.md
│   ├── ARCHITECTURE_v0.1.md
│   ├── FUNCTIONAL_REQUIREMENTS_v0.1.md
│   ├── NON_FUNCTIONAL_REQUIREMENTS_v0.1.md
│   ├── REDACTION_RULES_v0.1.md
│   ├── OCR_PIPELINE_v0.1.md
│   ├── DATA_FLOW_v0.1.md
│   ├── API_SPEC_v0.1.md
│   ├── SECURITY_v0.1.md
│   ├── TEST_CASES_v0.1.md
│   ├── UX_FLOW_v0.1.md
│   ├── ROADMAP.md
│   ├── CONTRIBUTING.md
│   └── DECISIONS.md
│
├── examples/
│   ├── sample_inputs/
│   ├── expected_outputs/
│   └── screenshots/
│
└── assets/
    ├── diagrams/
    ├── mockups/
    └── logos/

Requirements:
- Create placeholder content for every markdown file
- Include meaningful section headings in each document
- Keep the architecture technology-agnostic
- Focus on image-first redaction workflows
- Structure documentation for AI coding agents and open-source contributors
- Keep naming conventions clean and scalable
- Do not generate implementation code yet
- Emphasize modularity and maintainability
- Use concise but professional markdown formatting
- Include TODO placeholders where details are pending

Additional Guidance:
- PRODUCT_v0.1.md should define the product vision, users, MVP scope, and roadmap
- ARCHITECTURE_v0.1.md should define high-level system components and data movement
- FUNCTIONAL_REQUIREMENTS_v0.1.md should define exact expected behaviors
- REDACTION_RULES_v0.1.md should define what counts as sensitive information
- TEST_CASES_v0.1.md should contain realistic example inputs and expected outputs
- DECISIONS.md should be formatted as an architecture decision log
- UX_FLOW_v0.1.md should describe user interaction flows step-by-step
- SECURITY_v0.1.md should define privacy guarantees and threat considerations

The final output should look like a professional open-source project scaffold prepared for future development.

---

## Prompt 2 — Tech stack options analysis

You are a senior software architect and AI product engineer.
I am building an open-source project called `redact-ai`.
---
## Product Summary
redact-ai is a privacy-first tool that detects and redacts sensitive personal information (PII) from screenshots, images, PDFs, and text before users send them to AI tools like ChatGPT or Claude.
Core capabilities:
- OCR for images/screenshots
- PII detection (names, phone numbers, emails, IDs, financial/medical data)
- Redaction engine (blur/block/overlay)
- Safe output generation
- Future: browser extension + API + SaaS
---
## Your Task
Design and compare the MOST suitable tech stack options for building this system.
You MUST:
### 1. Provide 2–4 viable tech stack options
Each option should represent a different architectural approach, such as:
- Local-first CLI tool
- Python AI/ML-centric pipeline
- Hybrid API + frontend architecture
- Scalable SaaS-ready system
---
### 2. For EACH stack option include:
#### A. Stack Description
- Programming languages
- Core frameworks/libraries
- OCR approach/tools
- PII detection approach
- Image processing tools
- CLI/API/UI structure
#### B. Pros
- Strengths of the stack
- Performance advantages
- Developer experience
- Scalability potential
- Ecosystem maturity
#### C. Cons
- Weaknesses
- Complexity
- Maintenance overhead
- Deployment difficulty
- Tradeoffs
#### D. Best Fit
- When to choose this stack
- What stage of product it fits (MVP / scale / enterprise)
---
### 3. Final Recommendation Section
Provide:
- Recommended stack for MVP (v0.1)
- Recommended stack for scaling (v1.0+)
- Clear reasoning for both choices
---
## OUTPUT REQUIREMENT (IMPORTANT)
Instead of plain text output, you must generate a **Markdown file content** that is ready to be saved inside the repository.
### File details:
- File path: `/docs/TECH_STACK_OPTIONS_v0.1.md`
- Format: clean Markdown
- Must include:
  - Title
  - Sections as described above
  - Tables where useful
  - Clear headings
  - Professional documentation style
---
## Constraints
- Do NOT assume final business model
- Keep focus on MVP feasibility
- Prioritize OCR + image redaction use case
- Avoid over-engineered enterprise-only solutions
- Assume privacy-first, local-first preference is important
---
## Goal
Help select a tech stack that:
1. Enables fast MVP development
2. Supports accurate OCR + PII detection
3. Is modular and scalable
4. Can evolve into a production-ready system
---
## Output Format
Return ONLY the full Markdown file content for:
`/docs/TECH_STACK_OPTIONS_v0.1.md`

---

## Prompt 3 — Pivot v0.1 surface

I am still thinking that focussing on a PDF redaction on a web app will be better approach for already MVP

**Resolved scope** (after clarification in chat):

- App type: **local web UI** — Python server bound to `127.0.0.1` +
  a single drag-and-drop page in the user's existing browser.
- Input scope: **images stay primary** for v0.1; PDFs remain v0.3.
  ADR-001 not revisited.
- Privacy stance: **local-first preserved**. ADR-002 not revisited.

The decision is recorded as ADR-007 in
[`docs/DECISIONS.md`](./docs/DECISIONS.md).

---

## Prompt 4 — Build v0.1 MVP from the specs

This prompt is what an AI coding agent should be given to consume the
v0.1 design specs (`docs/*_v0.1.md`), the prescriptive build docs
(`docs/BUILD_SPEC_v0.1.md`, `docs/DETECTORS_v0.1.md`), and the example
fixtures (`examples/default_policy.yaml`,
`examples/manifest_example.json`), and produce the working MVP.

````text
You are implementing redact-ai v0.1 — a privacy-first preprocessing tool that detects and masks sensitive information in screenshots and images before users send them to an LLM. The repository at the current working directory is in a documentation-complete state; your job is to ship the MVP application end-to-end.

═══════════════════════════════════════════════════════════════════
AUTHORITATIVE SOURCES — read these before writing any code
═══════════════════════════════════════════════════════════════════

Read in this order. Treat them as the contract; do not deviate without recording an ADR.

1. README.md — product framing and architecture overview.
2. docs/PRODUCT_v0.1.md — vision, users, MVP scope.
3. docs/ARCHITECTURE_v0.1.md — pipeline shape (Ingest → OCR → Detect → Redact → Report).
4. docs/FUNCTIONAL_REQUIREMENTS_v0.1.md — every FR-x.y you must satisfy.
5. docs/NON_FUNCTIONAL_REQUIREMENTS_v0.1.md — every NFR-x.y you must satisfy.
6. docs/SECURITY_v0.1.md — privacy promises, threat model, §4a localhost hardening.
7. docs/DATA_FLOW_v0.1.md — trust zones, persistence rules.
8. docs/OCR_PIPELINE_v0.1.md — Document model and engine adapter contract.
9. docs/REDACTION_RULES_v0.1.md — categories and rule IDs.
10. docs/API_SPEC_v0.1.md — abstract types (Policy, Manifest, Finding…).
11. docs/UX_FLOW_v0.1.md — end-to-end user journey.
12. docs/TEST_CASES_v0.1.md — TC-001..TC-010 plus DT-001 determinism.
13. docs/TECH_STACK_OPTIONS_v0.1.md — chosen stack: Option A (Python local-first).
14. docs/DECISIONS.md — ADR-001..ADR-010. These are binding.

THEN read the two prescriptive build docs — these resolve every implementation choice the design specs left open:

15. docs/BUILD_SPEC_v0.1.md — project layout, pinned deps, policy schema, canonical data model, concrete HTTP API contract, manifest schema, redaction-style algorithms, bbox-merge algorithm, confidence mapping, error/warning catalogue, server CSRF/Origin enforcement, front-end copy/accessibility, test plan, and the suggested implementation order.
16. docs/DETECTORS_v0.1.md — regex, validation, label triggers, and confidence rules for every baseline rule (ID-001 through LO-001) plus the detector registry shape.

Reference fixtures (treat as canonical examples, not stubs):

17. examples/default_policy.yaml — the policy file the runtime ships and loads as id="default".
18. examples/manifest_example.json — canonical manifest shape; your output for TC-001 must match this structure.

═══════════════════════════════════════════════════════════════════
WHAT TO BUILD
═══════════════════════════════════════════════════════════════════

The v0.1 MVP is a single Python application that:

- Starts with `redact-ai` (or `python -m redact_ai`), binds a FastAPI server to 127.0.0.1 on an ephemeral port, and opens the user's default browser to the bound URL.
- Serves a single static drag-and-drop page from the same process.
- Accepts PNG/JPEG/WebP uploads via `POST /redact` (multipart, CSRF-protected).
- Runs the pipeline: Ingest → OCR (Tesseract) → Detect (every rule in DETECTORS_v0.1.md) → Bbox-merge → Redact → Manifest.
- Returns the redacted image plus a JSON manifest in the same response cycle (image bytes by default; full JSON envelope when `Accept: application/json`).
- Fails closed on any error that risks leaking sensitive content.
- Persists nothing except what the user explicitly downloads.
- Makes zero outbound network calls.

Out of scope (do not build): CLI subcommands beyond a stub, clipboard ingestion, folder watcher, PDF support, manifest signing, non-Latin scripts, photo/face redaction, telemetry of any kind. See BUILD_SPEC_v0.1.md §18.

═══════════════════════════════════════════════════════════════════
BINDING CONSTRAINTS — non-negotiable
═══════════════════════════════════════════════════════════════════

- Project layout: exactly as specified in BUILD_SPEC_v0.1.md §4. Use `src/redact_ai/`.
- Dependencies: pinned versions from BUILD_SPEC_v0.1.md §3.2. Generate `uv.lock`. No additions without an ADR.
- Python: 3.11 and 3.12 only.
- OCR engine: Tesseract via pytesseract (ADR-008). PaddleOCR adapter exists but only behind the `[ocr-paddle]` extra; it must load and run, but is not the recall baseline.
- Default policy posture: strict (ADR-009). LOW-confidence findings are still redacted.
- Server bind: 127.0.0.1 only. No env override. Reject non-loopback Host/Origin with 403/E_ORIGIN.
- CSRF: per-process token in cookie + meta tag, sent as `X-Redact-CSRF` header on POST /redact, compared with `secrets.compare_digest`.
- Redaction styles: implement `block`, `pixelate` (flat-fill mean), and `label`. `blur` is accepted by the schema but MUST downgrade to `block` and emit `W_STYLE_DOWNGRADED_TO_BLOCK` (BUILD_SPEC_v0.1.md §10.2 — blur on text is reversible).
- Manifest never contains raw matched text unless `verbose_report=true` is passed AND the response carries `W_VERBOSE_REPORT_ENABLED` (ADR-006).
- Logging: JSON-lines to stderr, never log image bytes or matched text. Apply the redaction filter from BUILD_SPEC_v0.1.md §14.5.
- Coverage: `pipeline/redact.py` and `pipeline/merge.py` must hit 100% line+branch. Overall ≥ 85%.

═══════════════════════════════════════════════════════════════════
EXECUTION PLAN — follow this order, commit after each step
═══════════════════════════════════════════════════════════════════

Use the implementation order in BUILD_SPEC_v0.1.md §19. Make a commit per step with a clear message referencing FR / NFR / BS / ADR IDs.

1. Scaffold: `pyproject.toml` (PEP 621 + scripts entry), `uv.lock` via `uv lock`, `src/redact_ai/` skeleton with empty modules per §4, `tests/` tree.
2. Models + policy loader: implement `models/document.py`, `models/findings.py`, `models/manifest.py`, `policy/schema.py`, `policy/loader.py`. Validate `examples/default_policy.yaml` round-trips.
3. Tesseract OCR adapter: `pipeline/ocr/base.py` (Protocol) and `pipeline/ocr/tesseract.py`. Implement preprocessing per OCR_PIPELINE_v0.1.md §5. Record the affine transform required by BUILD_SPEC_v0.1.md §7.3.
4. Detectors: one module per category in `pipeline/detect/`. Each detector implements DETECTORS_v0.1.md exactly. Add `pipeline/detect/registry.py`.
5. Bbox merge: `pipeline/merge.py` per BUILD_SPEC_v0.1.md §11. Add Hypothesis property tests for idempotence and order-independence.
6. Redactor: `pipeline/redact.py`. Implement the three live styles. Project bboxes back to input pixels. Pixel-leak test per BUILD_SPEC_v0.1.md §16.4.
7. Manifest builder: `pipeline/report.py`. Sort findings deterministically (page, y, x, rule_id). Exclude `created_at` from equivalence comparisons.
8. Server: `server/app.py`, `server/routes.py`, `server/middleware.py` (loopback + Host/Origin enforcement), `server/csrf.py`. Map errors to HTTP per BUILD_SPEC_v0.1.md §8.1. OpenAPI must match §8.
9. Static front-end: `server/static/index.html`, `app.js`, `styles.css`. Implement the copy strings in §15.2 verbatim. Meet WCAG AA contrast.
10. Test fixtures: generate synthetic inputs for TC-001..TC-010 via `tests/golden/_generate.py`. Write expected manifests (sans `created_at`). Implement DT-001 byte-equality test.
11. CI workflow: lint → mypy → unit → integration → golden, on Python 3.11 and 3.12, with Tesseract installed per platform.

After each step, run the relevant slice of the test suite and only proceed when it is green.

═══════════════════════════════════════════════════════════════════
DEFINITION OF DONE
═══════════════════════════════════════════════════════════════════

You are done when ALL of the following hold:

- `uv sync --extra dev` succeeds on a clean checkout (Python 3.11 and 3.12).
- `redact-ai` from a fresh shell starts the server, opens the browser, accepts a TC-001 upload via drag-drop, and returns a correctly redacted image plus a manifest matching `examples/manifest_example.json` in shape.
- `pytest -q` is green: all unit, integration, and golden tests pass; coverage gates met.
- `ruff check`, `ruff format --check`, and `mypy src` are clean.
- TC-001 through TC-010 all pass; DT-001 demonstrates byte-equal output across two runs.
- A request with a missing/invalid CSRF token gets 403/E_CSRF; a request with `Host: evil.example` gets 403/E_ORIGIN.
- A blur-style request returns a `block`-masked image with `W_STYLE_DOWNGRADED_TO_BLOCK`.
- An unsupported MIME type returns 415/E_INPUT_FORMAT with a non-empty `hint` field.
- No process writes user image bytes to disk during a request (verified by an integration test that monitors the temp dir).
- README "Quick start" section is added with: install, run, drag a screenshot, open the manifest. Keep it under 25 lines.

═══════════════════════════════════════════════════════════════════
GUARDRAILS
═══════════════════════════════════════════════════════════════════

- Do not invent dependencies, endpoints, fields, error codes, or rule IDs that are not in BUILD_SPEC_v0.1.md or DETECTORS_v0.1.md.
- Do not add telemetry, analytics, crash reporting, or any outbound network call. The default policy must not touch the network.
- Do not weaken the fail-closed semantics. If you cannot guarantee a safe redaction, return an error and produce no output image.
- Do not log raw input bytes, OCR text, or matched values.
- If you find a genuine spec gap that blocks progress, append a new ADR (ADR-011, ADR-012, …) to docs/DECISIONS.md explaining the decision before implementing.
- Create a new feature branch named `claude/build-mvp-v0.1` for this work.
- Commit frequently with descriptive messages that reference IDs (e.g. "Implement FI-001 PAN detector with Luhn check (FR-3.1, BS-12)").
- Do NOT open a pull request unless explicitly asked.

Begin by reading every file listed in the AUTHORITATIVE SOURCES section in order, then post a brief plan (≤ 200 words) confirming your understanding and listing any spec contradictions you noticed before writing code.
````
