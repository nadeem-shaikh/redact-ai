# MVP BUILD SPEC — redact-ai (v0.1)

> **Audience.** An autonomous coding agent (or a human implementing
> alongside one) tasked with shipping the v0.1 MVP described across
> the v0.1 spec set. This file is a brief; it does **not** restate
> the design — it tells you which milestones to build, in which
> order, against which acceptance gates.
>
> **Source of design truth.**
> [`TECHNICAL_DESIGN_v0.1.md`](./TECHNICAL_DESIGN_v0.1.md). Every
> implementation question — exact module paths, Pydantic stubs,
> adapter Protocols, the FastAPI surface, error envelope, manifest
> canonical form, redactor algorithm — resolves there. When this
> spec and the TDD disagree, the TDD wins.
>
> **Depends on the TDD review PR.** This spec cites several TDD
> sections (`§5.8` `/readyz`, `§9.2` soft OCR-stability check,
> `§10.3` `prefetch-models`) that ship in the TDD review PR
> (originally #7, replaced by #9 due to a build-environment
> push limitation). Once that PR merges into `dev`, every cite
> resolves; this file is intended to merge **after** it.
>
> **Source of behavioural truth.** The functional and non-functional
> requirements ([`FUNCTIONAL_REQUIREMENTS_v0.1.md`](./FUNCTIONAL_REQUIREMENTS_v0.1.md),
> [`NON_FUNCTIONAL_REQUIREMENTS_v0.1.md`](./NON_FUNCTIONAL_REQUIREMENTS_v0.1.md)),
> the rule taxonomy ([`REDACTION_RULES_v0.1.md`](./REDACTION_RULES_v0.1.md)),
> and the test-case catalogue
> ([`TEST_CASES_v0.1.md`](./TEST_CASES_v0.1.md)). Every stable ID
> (`FR-x.y`, `NFR-x.y`, `ID-001`, `CO-002`, `TC-001`, `ADR-007`,
> `E_INPUT_FORMAT`) is load-bearing. Do not invent new IDs; do not
> renumber existing ones.

---

## 1. Outcome

The MVP is **done** when every line of the Definition of Done
checklist in [`TECHNICAL_DESIGN_v0.1.md`](./TECHNICAL_DESIGN_v0.1.md)
§16 is ticked, with the proof that section names for each line
green in CI on the supported platform matrix.

There are no other acceptance gates. There are no deliverables
beyond what §16 names.

---

## 2. Operating constraints (do not violate)

These are non-negotiable for v0.1. Each derives from a merged ADR
and a published requirement. If a milestone's design seems to
require violating one of them, stop and ask the human reviewer.

- **Local-first by default** ([ADR-002](./DECISIONS.md)). The
  default pipeline runs entirely on-device; the localhost loopback
  counts as on-device. No outbound network calls in the default
  policy.
- **Image-first for v0.1** ([ADR-001](./DECISIONS.md)). PNG, JPEG,
  WebP only. PDFs are v0.3.
- **Local web UI surface** ([ADR-007](./DECISIONS.md), FR-9.x).
  The server binds `127.0.0.1` only. Never `0.0.0.0`. Never any
  external interface.
- **Fail closed on uncertainty** ([ADR-005](./DECISIONS.md),
  FR-8.1). On any error that risks leaking sensitive content,
  produce no output.
- **Modular pipeline** ([ADR-004](./DECISIONS.md)). Ingestor → OCR
  → Detector → Redactor → Reporter behind explicit contracts. New
  detectors join via the registry without touching the core.
- **Manifests exclude raw matched text by default**
  ([ADR-006](./DECISIONS.md)). `matched_text` populates only when
  `policy.verbose_report = true`.
- **No real PII anywhere.** Test assets, doc examples, built-in
  policies, log messages, generator outputs — all synthetic. If
  you find yourself typing a real-looking name, address, account,
  or key, stop.
- **No telemetry of user content.** The binary contains no
  telemetry endpoints. There is no opt-in switch for v0.1.

The technology picks (Python 3.11+, PaddleOCR default, Tesseract
opt-in via extras, FastAPI + Uvicorn, Pydantic v2, JSON policies,
strict default policy) are recorded inline in `TECHNICAL_DESIGN_v0.1.md`
§4. Do not re-litigate them; do not introduce a new ADR to record
them.

---

## 3. Workflow protocol

- **Branching.** Create one short-lived feature branch per
  milestone, named `feat/mvp-mN-<short-slug>` (e.g.,
  `feat/mvp-m1-skeleton`), branched from the latest `dev`.
- **Base.** Every PR's base is `dev`. Never push to `main`. Never
  commit on `dev` directly.
- **One milestone per PR.** Do not bundle. Reviewer (human or
  Codex) gates progression between milestones; do not start the
  next milestone until the current PR is merged.
- **PR contents.** Each PR contains code + tests + a checklist
  noting which Definition-of-Done lines from the TDD it satisfies
  and which it leaves for later milestones.
- **Commits.** Small, descriptive commit messages. Reference stable
  IDs in the body (e.g., "Implements FR-9.6 origin/host validator").
- **Test discipline.** A milestone's PR is incomplete if its tests
  do not run green locally before push.
- **Stop conditions.** If a milestone's acceptance is not
  reachable without re-opening a settled decision, stop and surface
  a question rather than guessing. Same for any ambiguity in the
  TDD: ask, do not improvise.

---

## 4. Milestones

Each milestone has **scope**, **files** (the modules that change),
and **acceptance** (the tests / checks that prove it). Files are
named after the package layout in `TECHNICAL_DESIGN_v0.1.md` §14.

### M1 — Skeleton

Goal: the package exists, installs, and is wired together. No
business logic. The MVP can be reasoned about as a build
artefact before any pipeline code is written.

**Scope**

- Project metadata and console script in `pyproject.toml`.
- The `redact_ai` package layout from the TDD §14 folder tree.
- The Pydantic v2 type stubs from TDD §6 (every public type, no
  business logic on them).
- The adapter Protocols from TDD §5 (`Ingestor`, `OcrEngine`,
  `Detector`, `Redactor`, plus the Reporter shape).
- The typed exception hierarchy from TDD §5.10 and the
  `ErrorEnvelope` mapping from TDD §6.7.
- Logging configuration and the `SafeFormatter` from TDD §5.11.
- The `redact-ai` console entrypoint from TDD §10 — `--help`,
  `--version`, no server start yet.

**Acceptance**

- An editable install on a clean Python 3.11 / 3.12 environment
  succeeds on Linux, macOS, and Windows.
- `redact-ai --version` prints the package version.
- `pytest -q` is green with placeholder tests that import every
  module without error.
- `ruff check` passes.
- `mypy redact_ai` passes under the strict configuration.

### M2 — OCR adapter (PaddleOCR)

Goal: the system can turn an image into a `Document`.

**Scope**

- `PaddleOcrEngine` per TDD §5.3, mapping the underlying engine's
  output into the `Document → Page → Block → Line → Token`
  hierarchy from `OCR_PIPELINE_v0.1.md`.
- The `Ingestor` per TDD §5.2, including EXIF stripping and the
  preservation of original input dimensions on `NormalisedImage`
  (TDD §6.3 — `BBoxTransform`, `input_width`, `input_height`).
- The `redact-ai prefetch-models` subcommand per TDD §10.3.
- Per-process serialisation lock around the engine call.

**Acceptance**

- A round-trip on a synthetic 1080p image yields a non-empty
  `Document` with token confidences in `[0.0, 1.0]`.
- The soft OCR-stability test from TDD §9.2 passes (≥ 99% text
  overlap, ≥ 0.95 per-token bbox IoU between two consecutive
  runs on the same input).
- `redact-ai prefetch-models` populates the local cache and
  re-runs are idempotent.
- The optional Tesseract adapter is gated behind the
  `[ocr-tesseract]` extras install and is not imported when not
  installed. This is exercised by the **optional-import boundary
  job** in §6, which installs `.[dev]` only and asserts that
  importing the Tesseract adapter fails with a clear typed error
  while `redact_ai` and the default PaddleOCR engine still import
  cleanly.

### M3 — Detectors

Goal: the system can identify sensitive content in a `Document`.

**Scope**

- All baseline detectors from TDD §7.1 strategy table, organised
  per `REDACTION_RULES_v0.1.md` categories: IDENTITY (ID-001 …
  ID-005), CONTACT (CO-001 … CO-003), FINANCIAL (FI-001 …
  FI-004 with Luhn and IBAN checksums), CREDENTIALS (CR-001 …
  CR-003), HEALTH (HE-001), LOCATION (LO-001).
- `BaseDetector` per TDD §7.2 and the registry per TDD §5.4.
- The confidence comparator from TDD §6.5 / §7.3 (low <
  medium < high).
- The overlap-collapse algorithm per TDD §7.4, populating
  `Finding.meta["also_matched"]`.
- The detector orchestration semantics from TDD §5.4 — single
  detector failures become `Warning(source="detector")`;
  `E_DETECTOR` only when the orchestrator itself cannot proceed.

**Acceptance**

- Per-rule unit tests for every CO / ID / FI / CR / HE / LO rule
  on synthetic strings, including positive cases **at every
  confidence band that rule is documented to emit** in `TECHNICAL_DESIGN_v0.1.md`
  §7.1 (some rules emit only `high`, e.g., FI-002, LO-001 —
  don't try to provoke a `low` from a high-only rule), plus at
  least one negative case per rule.
- A combined detector test on the TC-001 fixture surfaces the
  expected findings as published in `TEST_CASES_v0.1.md` —
  **IDENTITY: 1, FINANCIAL: 2** for TC-001 (the bank statement),
  no CONTACT findings on this fixture.
- An overlapping-finding test produces a single collapsed
  `Finding` whose `meta.also_matched` lists the other rule IDs
  in lexicographic order.
- A failing-detector test asserts the orchestrator continues and
  appends a `Warning(source="detector")` to the manifest.

### M4 — Redactor and Reporter

Goal: the system can produce a redacted image and a manifest.

**Scope**

- `BlockRedactor` per TDD §8, including:
  - Mapping each finding's bbox from normalised space to input
    space using the inverse of `NormalisedImage.transform`
    (FR-4.4).
  - Pixel-zero post-condition (FR-4.5) on the redacted regions,
    with the lossy-format read-back tolerance from TDD §8.1.
  - The `policy.fill_colour` field from TDD §6.5.
- `Reporter.build()` and `Reporter.canonical_form()` per TDD §5.6.
- `Manifest.runtime_version` populated from the package version.
- ADR-006 enforcement at write time — `Finding.matched_text` is
  emitted only when `policy.verbose_report` is true.

**Acceptance**

- Redacted-output dimensions equal input dimensions on every TC
  fixture (FR-4.4).
- The pixel-zero post-condition holds for every redacted region
  on every TC fixture (FR-4.5).
- The reporter's canonical form sorts findings and warnings as
  TDD §9.2 specifies, excludes `created_at`, and includes
  `input_hash` and `runtime_version`.
- DT-001 passes: replaying the same captured `Document` through
  Detectors → Redactor → Reporter twice yields byte-identical
  `output_image.bytes` and identical canonical-form hashes.
- A non-verbose run produces a manifest with no `matched_text`
  populated; a verbose run populates it.

### M5 — Local web server and drag-drop UI

Goal: the user-facing surface — a localhost browser experience
that drives the pipeline.

**Scope**

- The FastAPI app factory from TDD §5.8 (`create_app`, `run`,
  `ServerConfig`).
- Routes per TDD §5.8 — `POST /redact`, `GET /policies`,
  `GET /healthz`, `GET /readyz`, plus the static page at `GET /`.
- The `OriginHostValidator` middleware per TDD §13.2 — two
  allowlists, one for the `Origin` header and one for the `Host`
  fallback, decision logic per the TDD.
- The `CsrfValidator` middleware per TDD §13.3 — per-process
  token, constant-time comparison.
- The static drag-and-drop page per TDD — single HTML page,
  vanilla JS, multipart upload to `POST /redact`, manifest
  rendering, copy-to-clipboard / download / "redact another"
  affordances.
- The `redact-ai` console default invocation per TDD §10.1 —
  bind 127.0.0.1 with an ephemeral port, print the URL on
  stderr, open the user's default browser.

**Acceptance**

- A round-trip `POST /redact` on the TC-001 fixture (via httpx
  against the FastAPI app) returns a redacted image and a
  manifest matching TC-001's expected manifest in canonical
  form.
- A request with `Origin` outside the loopback allowlist is
  rejected with HTTP 403 and an `ErrorEnvelope` of
  `code = "E_POLICY"`, `stage = "server"`.
- A request without a CSRF token (or with a wrong one) is
  rejected with HTTP 403 / `E_POLICY`.
- `GET /healthz` returns 200 within the NFR-1.3 budget after
  process start (cold-start measured to first 200 from
  `/healthz`).
- `GET /readyz` returns 503 while OCR is warming and 200 once
  ready.
- An attempt to bind any host other than `127.0.0.1` fails fast
  with `E_POLICY` (defence-in-depth check, even though the
  `ServerConfig.host` Pydantic literal already prevents it).

### M6 — End-to-end and benchmarks

Goal: every TC-* fixture round-trips through the full pipeline,
the latency / memory budgets hold, and CI runs green on every
supported platform.

**Scope**

- End-to-end tests for TC-001 through TC-010 per
  `TEST_CASES_v0.1.md`, each driving the FastAPI app via httpx
  and asserting the manifest in canonical form.
- DT-001 in its post-OCR-replay form per TDD §9.2.
- A latency benchmark on a 1080p fixture asserting `pytest-benchmark`
  mean below the 3 s NFR-1.1 budget.
- A `tracemalloc`-based smoke test asserting peak heap below the
  1 GB NFR-1.2 ceiling on the largest fixture.
- A cold-start test asserting first-`200`-from-`/healthz` time
  below the 2 s NFR-1.3 budget.
- The CI workflow described in §6 below.

**Acceptance**

- Every TC fixture is green on Linux, macOS, and Windows × Python
  3.11 / 3.12.
- DT-001 is green.
- Latency, memory, and cold-start benchmarks pass on the matrix.
- `ruff check` and `mypy redact_ai` are green on every matrix
  cell.
- *(Supplementary, not a §1 release gate.)* The
  regenerator-stability guard from §5 below succeeds on a clean
  checkout of the matrix runners. Failure here flags a real
  regression but does not by itself block a release that
  otherwise meets every line of TDD §16.

---

## 5. Test asset generation

All test inputs are synthetic, generated programmatically from
Pillow. The repo never holds a real screenshot, a real ID, a real
account number, a real key, or a real photograph of a person.

**The generator.** A small generator module under
`tests/assets/_generators/` is responsible for emitting every TC's
input image and its expected manifest. The generator must be
deterministic — running it on a clean checkout in a fresh Python
environment must produce byte-identical outputs.

**Determinism contract.**

- A single bundled font file (DejaVu Sans, permissively licensed)
  shipped under `tests/assets/_generators/fonts/`, used for every
  TC. No system fonts.
- A fixed canvas size per TC. Explicit RGB tuples — no system
  theme influence, no transparency unless the TC specifically
  exercises an alpha channel.
- No randomness anywhere. No `time.time()` seeds, no UUIDs in
  output, no numbers derived from the running environment. Text
  strings, positions, font sizes, colours are constants in the
  generator source.
- Output per TC under `tests/assets/tc_NNN/` — the input image
  (PNG, 8-bit RGB, no metadata) and the expected manifest in
  canonical form per TDD §9.2.

**Repository discipline.** The generated bytes are committed.
Tests do not regenerate at test time; they read the committed
files. A regenerator-stability guard runs the generator on a
clean checkout and asserts the working tree under `tests/assets/`
has no diff. A regression in determinism is a red CI cell — but
this guard is **supplementary verification**, not a §1 release
gate; the canonical Definition of Done in §1 remains TDD §16.

**Per-TC files.**

- The input image: what the pipeline ingests.
- The expected manifest: canonical form, used as the assertion
  target for end-to-end tests.
- A short generator-notes file: the synthetic strings used,
  layout decisions, anything an auditor would want to verify
  the absence of real PII.

---

## 6. CI matrix

The full GitHub Actions workflow ships under `.github/workflows/`
and is described here as a checklist. The shape is fixed; the
exact YAML is mechanical and lands as part of M6.

- **Triggers.** Every push and every pull request.
- **Matrix.** Linux, macOS, Windows by Python 3.11 and 3.12.
  `fail-fast` is off so that a single platform regression does
  not mask others.
- **Ordered steps per cell — required (block merge on red).**
  1. Repo checkout.
  2. The matrix-selected Python is set up.
  3. Tesseract is installed via the platform's standard package
     manager. CI uses the **Chocolatey** row on Windows (the
     `windows-latest` runner ships Chocolatey by default; Scoop
     in the `CONTRIBUTING.md` §10 table is a contributor-only
     convenience and is **not** used in CI). Linux and macOS
     mirror the corresponding rows in the §10 table.
  4. Editable install of the project with the development and
     opt-in OCR extras enabled (`pip install -e ".[dev,ocr-tesseract]"`).
  5. The `redact-ai prefetch-models` subcommand is run to warm
     both engines so latency and readiness tests are not
     dominated by first-run weight download.
  6. Lint via Ruff.
  7. Type-check via mypy on the `redact_ai` package.
  8. Test suite via pytest.
- **Ordered steps per cell — supplementary (do not block merge
  on red, but flag a regression).**
  9. The regenerator-stability guard from §5. Marked supplementary
     to stay consistent with §1 and §5: a determinism-only failure
     here surfaces a real regression, but the canonical Definition
     of Done remains TDD §16.
- **Optional-import boundary job (separate, required).** A small
  additional CI job — Linux + Python 3.12 only, fast — installs
  the project **without** the `[ocr-tesseract]` extra
  (`pip install -e ".[dev]"`) and asserts:
  - `import redact_ai` succeeds.
  - `import redact_ai.ocr.paddle` succeeds (default engine).
  - Importing the Tesseract adapter fails with a clear typed
    error (e.g., `pytesseract` `ModuleNotFoundError` surfaces a
    `RedactError` with `code = "E_IO"` and a hint pointing at
    the `[ocr-tesseract]` extras install).
  This is the only CI cell that proves M2's optional-import
  acceptance gate (§4 M2). Without it, accidentally removing the
  optional-import boundary in `redact_ai/ocr/__init__.py` would
  go unnoticed.

A cell is green when every **required** step in that cell is
green. A red required step blocks merge; a red supplementary
step is reported as a flag but does not block merge.

---

## 7. Things you must not do

- Do not modify functional, non-functional, rule, test-case, or
  ADR identifiers in any of the v0.1 docs. They are referenced
  from across the spec set; renaming breaks every cross-reference.
- Do not introduce a new ADR. The TDD's picks are inline; that
  was a deliberate choice.
- Do not reach for NLP, transformer, or hosted-cloud detectors in
  v0.1. The detector strategy in TDD §7 is regex / dictionary /
  checksum / entropy only.
- Do not bind the server to anything other than `127.0.0.1`. No
  configuration option exposes a wider bind.
- Do not log raw OCR text, matched text, or bounding boxes. The
  `SafeFormatter` strips them; do not work around it.
- Do not write user-supplied bytes to disk except at a path the
  user has explicitly chosen.
- Do not commit real PII anywhere — code, tests, comments,
  policies, generator inputs, README examples, commit messages.
- Do not depend on a network **during the pytest run**. The
  default policy has zero outbound network calls and the test
  suite must respect that. The CI `prefetch-models` step in §6
  runs **before** pytest as a setup phase that warms the local
  weight cache; it is not part of the test run, and a fresh
  environment without network must still pass `pytest -q` once
  the cache is populated by any means (CI artifact, vendored
  archive, or earlier prefetch).
- Do not silently widen scope. PDFs, NLP detectors, custom-rule
  authoring, browser extensions, and clipboard ingestion are out
  of v0.1. If a milestone seems to need them, stop and surface
  a question.

---

## 8. Open questions (deliberately unresolved in v0.1)

These are catalogued across the v0.1 spec set with `TODO` markers
in their source documents. Do **not** close them in the MVP
build. They each require a product, UX, or scaling decision that
sits outside an implementing agent's authority.

- Default policy strictness as a user-tunable knob.
- Manifest signing.
- Streaming variant for very large inputs.
- RTL and non-Latin script roadmap.
- OCR sandboxing.
- Sealed mode (manifest hidden from logs).
- Editable review screen on the web UI.
- Custom-detector authoring tooling.
- Plugin marketplace.
- Public benchmark corpus.

If a milestone seems to require closing one of these, the
implementing agent should stop and surface a question to the
human reviewer rather than picking an answer.

---

## 9. References

| Document | Purpose |
| --- | --- |
| [`TECHNICAL_DESIGN_v0.1.md`](./TECHNICAL_DESIGN_v0.1.md) | Source of design truth — module shapes, type stubs, FastAPI handlers, error envelope, manifest canonical form, redactor algorithm. |
| [`PRODUCT_v0.1.md`](./PRODUCT_v0.1.md) | Vision, users, MVP scope, success criteria. |
| [`ARCHITECTURE_v0.1.md`](./ARCHITECTURE_v0.1.md) | High-level pipeline contracts. |
| [`FUNCTIONAL_REQUIREMENTS_v0.1.md`](./FUNCTIONAL_REQUIREMENTS_v0.1.md) | What the system must do — `FR-x.y` IDs cited throughout this brief. |
| [`NON_FUNCTIONAL_REQUIREMENTS_v0.1.md`](./NON_FUNCTIONAL_REQUIREMENTS_v0.1.md) | Quality attributes — `NFR-x.y` budgets cited in the milestones. |
| [`REDACTION_RULES_v0.1.md`](./REDACTION_RULES_v0.1.md) | Rule taxonomy — every rule ID used in M3. |
| [`OCR_PIPELINE_v0.1.md`](./OCR_PIPELINE_v0.1.md) | Document model contract used by M2. |
| [`DATA_FLOW_v0.1.md`](./DATA_FLOW_v0.1.md) | Trust zones, persistence rules. |
| [`API_SPEC_v0.1.md`](./API_SPEC_v0.1.md) | Public types and HTTP routes. |
| [`SECURITY_v0.1.md`](./SECURITY_v0.1.md) | Threat model, localhost server hardening. |
| [`TEST_CASES_v0.1.md`](./TEST_CASES_v0.1.md) | TC-001 … TC-010 expected behaviour, used in M3 / M5 / M6. |
| [`UX_FLOW_v0.1.md`](./UX_FLOW_v0.1.md) | The user's path through the local web UI. |
| [`TECH_STACK_OPTIONS_v0.1.md`](./TECH_STACK_OPTIONS_v0.1.md) | Stack rationale and constraints. |
| [`DECISIONS.md`](./DECISIONS.md) | The ADR log. |
| [`ROADMAP.md`](./ROADMAP.md) | What is in v0.2, v0.3, etc. |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Project conventions and contributor workflow. |
