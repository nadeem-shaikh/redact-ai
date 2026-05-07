# TECHNICAL DESIGN — redact-ai (v0.1 MVP)

> Status: **Implementation-ready blueprint.** Translates the
> technology-agnostic v0.1 spec set into concrete Pydantic types,
> adapter Protocols, FastAPI handlers, drag-drop static UI, pytest
> layout, `pyproject.toml` outline, and CI matrix. Anchored on
> [ADR-001](./DECISIONS.md) (image-first), [ADR-002](./DECISIONS.md)
> (local-first), [ADR-003](./DECISIONS.md) (technology-agnostic
> specs), [ADR-004](./DECISIONS.md) (modular pipeline),
> [ADR-005](./DECISIONS.md) (fail-closed), and
> [ADR-007](./DECISIONS.md) (local web UI surface).

---

## 1. Overview

`redact-ai` v0.1 is a privacy-first preprocessing pipeline that
takes a screenshot or other image, runs OCR, detects sensitive
content with deterministic regex/dictionary detectors, masks the
sensitive regions in pixel space, and returns the redacted image
plus a structured manifest. The system is **local-first by default**
(ADR-002): the entire pipeline runs in a single Python process on
the user's machine, with no outbound network in the default policy.

The user-visible surface for v0.1 is a **local web UI** (ADR-007):
the `redact-ai` console command starts a FastAPI server bound to
`127.0.0.1`, opens the user's default browser at the bound URL, and
serves a single drag-and-drop HTML page that talks to the server
over the loopback interface. The CLI subcommand `redact-ai run`
described in [`API_SPEC_v0.1.md`](./API_SPEC_v0.1.md) §5 is
**reserved for v0.2**.

This document is the engineering blueprint for the v0.1 build.
Intended audience: implementing engineers and AI coding agents. It
**does not replace** [`ARCHITECTURE_v0.1.md`](./ARCHITECTURE_v0.1.md)
(high-level pipeline contracts) or
[`API_SPEC_v0.1.md`](./API_SPEC_v0.1.md) (public types and
endpoints). It complements them by closing four spec TODOs (the
OCR `Hints` and `NormalisedImage` schemas, the `Policy` JSON
schema, the error-envelope shape, and the manifest-equivalence
definition for DT-001) and by publishing concrete picks where the
v0.1 specs are deliberately technology-agnostic per ADR-003.

The most consequential pick: **PaddleOCR is the default v0.1 OCR
engine**. Tesseract is demoted to an opt-in `[ocr-tesseract]`
extras install. PaddleOCR raises the default install footprint
from ~50–80 MB to ~500 MB–1 GB and complicates Windows / arm64 CI
because of `paddlepaddle` wheel availability. Accepted in exchange
for materially higher OCR accuracy on real-world screenshots,
especially low-DPI captures and non-Latin scripts. This **diverges**
from the current
[`TECH_STACK_OPTIONS_v0.1.md`](./TECH_STACK_OPTIONS_v0.1.md), which
positions PaddleOCR as opt-in extras; a follow-up PR will reconcile
the tech-stack doc.

---

## 2. Scope

### 2.1 In Scope

- The v0.1 [`ROADMAP.md`](./ROADMAP.md) checklist items: OCR
  adapter implementation, baseline detectors for IDENTITY /
  CONTACT / FINANCIAL / CREDENTIALS, default + strict policies,
  solid-block redactor, manifest generator, local web UI, and
  end-to-end test cases TC-001…TC-010 + DT-001.
- Closing the following spec TODOs:
  - [`OCR_PIPELINE_v0.1.md`](./OCR_PIPELINE_v0.1.md): concrete
    `Hints` and `NormalisedImage` schemas — see §6.
  - [`ARCHITECTURE_v0.1.md`](./ARCHITECTURE_v0.1.md) §6: `Policy`
    JSON schema — see §6.
  - [`API_SPEC_v0.1.md`](./API_SPEC_v0.1.md): `ErrorEnvelope` JSON
    shape and HTTP status mapping — see §6 and §13.
  - [`TEST_CASES_v0.1.md`](./TEST_CASES_v0.1.md) (DT-001):
    canonical-form rules for manifest equivalence under determinism
    testing — see §9.
- The local web UI surface (FR-9.1 … FR-9.7): FastAPI server,
  `Origin` / `Host` validator, CSRF, static drag-and-drop page,
  ephemeral-port binding.

### 2.2 Out of Scope

- PDF input and layout-aware redaction for tables / forms (v0.3).
- The `redact-ai run --input ...` subcommand (v0.2) and other
  power-user surfaces — clipboard ingestion, folder watcher.
- Browser extension and OS share-sheet integration (v0.4).
- User-defined detectors and policy authoring UI (v0.5).
- The product / UX / scaling open questions catalogued across the
  v0.1 spec set (default-policy strictness as a user-tunable knob,
  manifest signing, streaming variant, RTL / non-Latin scripts
  roadmap, OCR sandboxing, sealed mode, editable review screen,
  and others). Each remains in its source doc with a TODO marker;
  this TDD does not close them.
- New ADRs. The picks in §4 are recorded inline rather than
  promoted to ADRs.

---

## 3. System Architecture

```text
┌──────────────── USER DEVICE (trusted zone) ────────────────────┐
│                                                                │
│  Browser ──drag/drop──▶ FastAPI (127.0.0.1:<ephemeral-port>)   │
│                              │                                 │
│                              ▼                                 │
│   Ingestor → OCR Engine → Detector × N → Redactor → Reporter   │
│                                       │                        │
│                  ◀──── redacted image + manifest ──────────────│
│                                                                │
└────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                      External AI tool (untrusted)
```

Every box runs inside one Python process. The loopback HTTP hop
(`127.0.0.1`) does not traverse a network interface. No
intermediate state is written to disk by default; persistence
happens only when the user explicitly chooses an output path
(FR-7.1, FR-7.3). The pipeline fails closed on any error that
risks leaking sensitive content (ADR-005, FR-8.1).

---

## 4. Tech Stack

| Concern | Pick | Trade-off accepted |
| --- | --- | --- |
| Language | Python 3.11+ | Drops 3.10 and earlier; preferred for `Self` typing, exception groups, perf |
| Package | `redact_ai` (PyPI: `redact-ai`) | None |
| OCR engine (default) | **PaddleOCR** (`paddleocr` + `paddlepaddle`) | +0.5–1 GB install, harder Windows / arm64 CI; bought higher real-screenshot accuracy |
| OCR engine (fallback) | Tesseract via `[ocr-tesseract]` extras | None |
| Image library | Pillow (≥ 10.x) | None |
| Web framework | FastAPI + Uvicorn | None |
| Multipart parsing | `python-multipart` | None |
| Validation | Pydantic v2 | None |
| Policy file format | JSON | YAML deferred to v0.2 (avoids extra dep) |
| Default policy | `strict` | Bias toward recall on the v0.1 PII set |
| Test framework | `pytest`, `pytest-asyncio`, `pytest-benchmark`, `httpx`, Pillow `ImageChops` | None |
| Lint / type | `ruff`, `mypy --strict` | None |

**Note on divergence from `TECH_STACK_OPTIONS_v0.1.md`.** That doc
currently positions PaddleOCR as opt-in `[ocr-paddle]` extras and
Tesseract as the v0.1 baseline. This TDD picks the inverse for the
reasons in the trade-off column. A follow-up PR will reconcile the
tech-stack doc; do not treat the divergence as authoritative until
it lands.

---

## 5. Module Design

The `redact_ai/` package is layered to mirror the pipeline contracts
in `ARCHITECTURE_v0.1.md` §3. Each module exposes a `Protocol` plus
one or more concrete implementations.

### 5.1 `redact_ai.types`

Pydantic v2 models for every public type. No business logic; pure
data. Re-exported under the package root so consumers can write
`from redact_ai import Manifest`. Full schema in §6.

### 5.2 `redact_ai.ingestor`

```python
from typing import Protocol

class Ingestor(Protocol):
    def ingest(self, source: ImageInput) -> NormalisedImage: ...
```

`DefaultIngestor` validates MIME (FR-1.1, FR-1.2), strips EXIF
(FR-1.3), normalises orientation, decodes once into a Pillow
`Image`, and emits a `NormalisedImage`. Unsupported MIME types
raise `InputFormatError` with `code = "E_INPUT_FORMAT"`.

### 5.3 `redact_ai.ocr`

```python
class OcrEngine(Protocol):
    def recognise(self, image: NormalisedImage, hints: Hints) -> Document: ...
```

Implementations:

- `PaddleOcrEngine` (default) — wraps `paddleocr.PaddleOCR`,
  serialises calls behind a per-process `threading.Lock`, maps
  PaddleOCR's nested output into the `Document → Page → Block →
  Line → Token` hierarchy from `OCR_PIPELINE_v0.1.md`.
- `TesseractOcrEngine` (opt-in via `[ocr-tesseract]`) — wraps
  `pytesseract.image_to_data`; same output contract.

Engine selection happens at app-factory time via a config string
(`config.ocr_engine = "paddle"` is the default).

### 5.4 `redact_ai.detect`

```python
class Detector(Protocol):
    rule_id: str
    category: Category
    def detect(self, doc: Document, policy: Policy) -> list[Finding]: ...
```

One file per category: `identity.py`, `contact.py`, `financial.py`,
`credentials.py`, plus `health.py` and `location.py` scaffolds for
deferred rules. `registry.py` maps `rule_id → Detector` and exposes
`iter_active_detectors(policy: Policy) -> Iterable[Detector]`.

Adding a new detector in v0.1 means adding a class, registering
its `rule_id` in `registry.py`, and adding a row to the policy
schema's `detectors` allow-list (NFR-6.3).

### 5.5 `redact_ai.redact`

```python
class Redactor(Protocol):
    def redact(
        self,
        image: NormalisedImage,
        findings: list[Finding],
        style: RedactionStyle,
    ) -> ImageOutput: ...
```

`BlockRedactor` is the only style implemented in v0.1 (FR-4.2).
`BlurRedactor`, `PixelateRedactor`, `LabelRedactor` exist as stubs
that raise `NotImplementedError` (v0.2; ROADMAP).

### 5.6 `redact_ai.report`

```python
class Reporter:
    def build(
        self,
        policy: Policy,
        input_hash: str,
        findings: list[Finding],
        warnings: list[Warning],
    ) -> Manifest: ...

    def canonical_form(self, manifest: Manifest) -> bytes: ...
```

Produces the `Manifest` and exposes `canonical_form()` for DT-001.
Honours ADR-006: `matched_text` is included only when
`policy.verbose_report = True`.

### 5.7 `redact_ai.policy`

`load(path_or_name: str) -> Policy`. Built-in policies live in
`redact_ai/policy/builtins/{default.json, strict.json}` and are
shipped as package data. Validation errors raise `PolicyError`
(`code = "E_POLICY"`).

### 5.8 `redact_ai.server`

FastAPI app factory + routes + middleware + static assets.

```python
class ServerConfig(BaseModel):
    host: Literal["127.0.0.1"] = "127.0.0.1"
    port: int = 0                # ephemeral by default
    ocr_engine: Literal["paddle", "tesseract"] = "paddle"
    log_level: str = "INFO"

def create_app(config: ServerConfig) -> FastAPI: ...
def run(config: ServerConfig) -> None: ...
```

Routes registered: `POST /redact`, `GET /policies`, `GET /healthz`,
plus the static page at `GET /`. Middleware order (outermost
first): `OriginHostValidator`, `CsrfValidator`, framework-default.

### 5.9 `redact_ai.cli`

`redact-ai` console entrypoint. `main()` parses args, builds
`ServerConfig`, calls `server.run()`, and opens the browser via
`webbrowser.open`. See §10 for the flag set.

### 5.10 `redact_ai.errors`

Typed exception hierarchy:

```python
class RedactError(Exception):
    code: str   # E_INPUT_FORMAT | E_OCR | E_DETECTOR | E_REDACTION | E_IO | E_POLICY
    stage: str  # ingestor | ocr | detector | redactor | reporter | server
    hint: str | None = None

class InputFormatError(RedactError): ...   # code = "E_INPUT_FORMAT"
class OcrError(RedactError): ...           # code = "E_OCR"
class DetectorError(RedactError): ...      # code = "E_DETECTOR"
class RedactionError(RedactError): ...     # code = "E_REDACTION"
class IoError(RedactError): ...            # code = "E_IO"
class PolicyError(RedactError): ...        # code = "E_POLICY"
```

A boundary handler in `server.app` maps each to an `ErrorEnvelope`
JSON response with the HTTP status from §13.

### 5.11 `redact_ai.logging`

`configure_logging(level: str)` installs a `logging.config.dictConfig`
with a `SafeFormatter` that strips any record fields named `text`,
`matched_text`, or `bbox` (NFR-8.2). Structured fields surfaced to
logs: `stage`, `rule_id`, `policy_id`, `duration_ms`,
`request_id`.

---

## 6. Data Structures

All public types are Pydantic v2 models in `redact_ai.types`. Field
names match `API_SPEC_v0.1.md` §3 verbatim where defined; new
fields are introduced only for the four schema TODOs this doc
closes.

### 6.1 Geometry

```python
from pydantic import BaseModel, ConfigDict

class Box(BaseModel):
    """Pixel-space rectangle. Coordinates are integers in the
    coordinate system of the post-preprocessing image."""
    x: int
    y: int
    w: int
    h: int

    model_config = ConfigDict(frozen=True)
```

### 6.2 OCR document model

```python
class Token(BaseModel):
    id: str            # stable: hash(page_index, x, y, text)[:16]
    text: str
    bbox: Box
    confidence: float  # in [0.0, 1.0]

class Line(BaseModel):
    id: str
    bbox: Box
    tokens: list[Token]

class Block(BaseModel):
    id: str
    bbox: Box
    lines: list[Line]

class Page(BaseModel):
    index: int        # 0-based; always 0 in v0.1 (single-image input)
    width: int
    height: int
    blocks: list[Block]

class Document(BaseModel):
    pages: list[Page]
    language: str = "en"
```

### 6.3 OCR adapter inputs (closes `OCR_PIPELINE_v0.1.md` TODO)

```python
from typing import Literal

class NormalisedImage(BaseModel):
    bytes: bytes
    width: int
    height: int
    channels: Literal[1, 3, 4]
    dpi: int                                  # post-normalisation DPI
    rotation: Literal[0, 90, 180, 270] = 0
    source_format: Literal["png", "jpeg", "webp"]

class Hints(BaseModel):
    language: str = "en"
    expected_orientation: Literal["auto", 0, 90, 180, 270] = "auto"
    deskew: bool = True
    denoise: bool = True
    target_dpi: int = 300
```

### 6.4 Image input / output

```python
from pathlib import Path

class ImageInput(BaseModel):
    source: Literal["file", "bytes", "clipboard"]
    mime_type: Literal["image/png", "image/jpeg", "image/webp"]
    bytes: bytes
    path: Path | None = None

class ImageOutput(BaseModel):
    mime_type: Literal["image/png", "image/jpeg", "image/webp"]
    bytes: bytes
    path: Path | None = None
```

### 6.5 Policy (closes `ARCHITECTURE_v0.1.md` §6 TODO)

```python
from typing import Any

RuleId = str                                  # "ID-001", "CO-002", ...
Confidence = Literal["low", "medium", "high"]
RedactionStyle = Literal["block", "blur", "pixelate", "label"]

class DetectorRef(BaseModel):
    id: RuleId
    enabled: bool = True
    threshold: Confidence = "medium"
    overrides: dict[str, Any] = {}

class Policy(BaseModel):
    id: str                                   # "default", "strict", or user-supplied
    version: str                              # semver, e.g. "0.1.0"
    description: str = ""
    detectors: list[DetectorRef]
    redaction_style: RedactionStyle = "block"
    strict: bool = True                       # v0.1 default
    verbose_report: bool = False              # ADR-006
```

`default.json`:

```json
{
  "id": "default",
  "version": "0.1.0",
  "description": "v0.1 strict baseline: all CO/ID/FI/CR rules on, HE-001 on.",
  "detectors": [
    { "id": "ID-001", "enabled": true, "threshold": "medium" },
    { "id": "ID-002", "enabled": true, "threshold": "medium" },
    { "id": "ID-003", "enabled": true, "threshold": "medium" },
    { "id": "ID-004", "enabled": true, "threshold": "medium" },
    { "id": "ID-005", "enabled": true, "threshold": "medium" },
    { "id": "CO-001", "enabled": true, "threshold": "low" },
    { "id": "CO-002", "enabled": true, "threshold": "low" },
    { "id": "CO-003", "enabled": true, "threshold": "medium" },
    { "id": "FI-001", "enabled": true, "threshold": "low" },
    { "id": "FI-002", "enabled": true, "threshold": "low" },
    { "id": "FI-003", "enabled": true, "threshold": "medium" },
    { "id": "FI-004", "enabled": true, "threshold": "medium" },
    { "id": "HE-001", "enabled": true, "threshold": "medium" },
    { "id": "CR-001", "enabled": true, "threshold": "medium" },
    { "id": "CR-002", "enabled": true, "threshold": "low" },
    { "id": "CR-003", "enabled": true, "threshold": "low" },
    { "id": "LO-001", "enabled": true, "threshold": "medium" }
  ],
  "redaction_style": "block",
  "strict": true,
  "verbose_report": false
}
```

`strict.json` is identical to `default.json` for v0.1 (the bias is
already strict). It exists as a named alias so users can write
`--policy strict` explicitly. A future "lenient" preset would land
as a separate file.

### 6.6 Detection, result, and manifest

```python
from datetime import datetime

Category = Literal[
    "IDENTITY", "CONTACT", "FINANCIAL", "HEALTH",
    "CREDENTIALS", "LOCATION", "CUSTOM",
]

class Finding(BaseModel):
    id: str                                   # stable per-finding id
    category: Category
    rule_id: RuleId
    bbox: Box
    confidence: Confidence
    matched_text: str | None = None           # only when verbose_report=True

class Warning(BaseModel):
    code: str
    message: str
    source: Literal["ingestor", "ocr", "detector", "redactor", "reporter", "server"]

class Stats(BaseModel):
    redactions_total: int
    by_category: dict[Category, int]

class Manifest(BaseModel):
    policy_id: str
    policy_version: str
    input_hash: str                           # sha256, hex
    created_at: datetime                      # ISO 8601, UTC
    stats: Stats
    findings: list[Finding]
    warnings: list[Warning] = []

class RedactionResult(BaseModel):
    output_image: ImageOutput
    manifest: Manifest
    warnings: list[Warning] = []
```

### 6.7 Error envelope (closes `API_SPEC_v0.1.md` TODO)

Returned on any `4xx` / `5xx` from the local HTTP API.

```python
class ErrorBody(BaseModel):
    code: Literal[
        "E_INPUT_FORMAT", "E_OCR", "E_DETECTOR",
        "E_REDACTION", "E_IO", "E_POLICY",
    ]
    message: str
    stage: Literal["ingestor", "ocr", "detector", "redactor", "reporter", "server"]
    hint: str | None = None

class ErrorEnvelope(BaseModel):
    error: ErrorBody
```

JSON shape:

```json
{
  "error": {
    "code": "E_INPUT_FORMAT",
    "message": "Unsupported input format: image/heic",
    "stage": "ingestor",
    "hint": "Try PNG, JPEG, or WebP."
  }
}
```

HTTP status mapping is in §13.

---

## 7. Detection Engine Design

Detectors are deterministic; no ML in v0.1. Each `Detector` runs
once over the `Document` for its category. Output `Finding`s carry
a confidence band (`low | medium | high`) consumed by the redactor
according to `policy.strict`.

### 7.1 Strategy table

| Rule ID | Strategy | Confidence basis |
| --- | --- | --- |
| CO-001 (email) | Regex (RFC 5322 subset) | `high` if domain valid, `medium` otherwise |
| CO-002 (phone, intl) | Regex + libphonenumber-style heuristics | `medium` / `high` |
| CO-003 (postal address) | Multi-token + bbox proximity + dictionary | `medium` |
| ID-001 (full names) | First-name + last-name dictionaries + casing | `medium` |
| ID-002 (DOB) | Multi-format date regex + plausibility | `high` |
| ID-003 (gov ID, generic) | Format heuristics by locale (default `en-US`) | `medium` |
| ID-004 (passport) | Locale-aware format | `medium` / `high` |
| ID-005 (driver's licence) | Locale-specific format | `medium` |
| FI-001 (PAN) | Regex + Luhn checksum | `high` (Luhn=true) |
| FI-002 (IBAN) | Regex + mod-97 checksum | `high` |
| FI-003 (bank acct) | Locale-specific format | `medium` |
| FI-004 (CVV+expiry adjacent to PAN) | Bbox proximity to FI-001 finding | `high` |
| CR-001 (high-entropy token) | Length floor + Shannon entropy | `medium` / `high` |
| CR-002 (SSH private key block) | Block-marker regex (`-----BEGIN ... PRIVATE KEY-----`) | `high` |
| CR-003 (cloud key prefix) | Prefix table (`AKIA`, `AIza`, `xoxb-`, ...) + length | `high` |
| HE-001 (medical record number) | Locale-specific format | `medium` |
| LO-001 (GPS coordinates) | Regex + plausibility (lat ∈ [-90, 90], lon ∈ [-180, 180]) | `high` |

### 7.2 Base class outline

```python
class BaseDetector:
    rule_id: str
    category: Category

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        ref = next(d for d in policy.detectors if d.id == self.rule_id)
        if not ref.enabled:
            return []
        findings: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    findings.extend(self._scan_line(line, ref))
        return [f for f in findings if self._passes_threshold(f, ref.threshold)]

    # Subclass hook
    def _scan_line(self, line: Line, ref: DetectorRef) -> list[Finding]: ...
```

### 7.3 Confidence behaviour

| `policy.strict` | Finding confidence | Behaviour |
| --- | --- | --- |
| `True` | `low` | Redact + emit `low_confidence` warning |
| `True` | `medium` / `high` | Redact |
| `False` | `low` | Skip + emit `low_confidence_skipped` warning |
| `False` | `medium` / `high` | Redact |

A finding's confidence MUST be at or above its `DetectorRef.threshold`
to enter the redactor pipeline. The threshold is independent of
`policy.strict`, which only governs how `low`-confidence findings
are treated.

### 7.4 Overlap collapse

FR-3.5 requires that overlapping findings collapse into a single
masked region. Algorithm:

1. Compute IoU (intersection-over-union) for every pair of findings.
2. Build connected components where edges have `IoU ≥ 0.5`.
3. Collapse each component to one `Finding` with:
   - `bbox` = bounding rectangle of the component.
   - `rule_id` = highest-confidence finding's `rule_id`; ties
     broken by lexicographic `rule_id` for determinism.
   - `category` = corresponding category.
   - `confidence` = highest-confidence band in the component.
   - `meta.also_matched` = list of the other `rule_id`s.

### 7.5 Pluggability

Adding a new detector in v0.1 means:

1. Adding a `BaseDetector` subclass in the relevant category file.
2. Registering its `rule_id` in `redact_ai/detect/registry.py`.
3. Adding a `DetectorRef` row to the policy schema's `detectors`
   allow-list (NFR-6.3).

No core pipeline change required.

---

## 8. Redaction Engine Design

`BlockRedactor` is the v0.1 default. It draws solid rectangles over
each `Finding` bbox and verifies the result.

### 8.1 Algorithm

1. Open the original image bytes with Pillow, preserving mode and
   dimensions (FR-4.4).
2. Build an `ImageDraw.Draw` context.
3. For each `Finding`:
   - Compute the masked rectangle (snap bbox to integer pixels).
   - `draw.rectangle((x, y, x+w-1, y+h-1), fill=fill_colour)` where
     `fill_colour` defaults to `#000000` and is configurable via
     `policy.detectors[*].overrides["fill"]`.
4. **Post-condition check (FR-4.5).** For each masked rectangle,
   sample every pixel and assert it equals `fill_colour`. If any
   pixel differs, raise `RedactionError` (`E_REDACTION`) and
   produce no output (ADR-005).
5. Re-encode in the input format (FR-7.1). For lossy formats
   (JPEG, WebP), encode at quality 95 with a re-encode→decode→
   re-check loop to confirm the masked pixels survive
   compression.

### 8.2 Future styles (v0.2)

`BlurRedactor`, `PixelateRedactor`, `LabelRedactor` are scaffolded
as `Redactor` subclasses that raise `NotImplementedError` in v0.1
to keep their entry points stable.

---

## 9. Pipeline Design

```text
ImageInput
   │
   ▼
[Ingestor]  ──▶  NormalisedImage
                       │
                       ▼
                 [OcrEngine]  ──▶  Document
                                       │
                                       ▼
                                 [Detector × N]  ──▶  list[Finding]
                                                          │
                                                          ▼
                                                    [Redactor]  ──▶  ImageOutput
                                                                          │
                                                                          ▼
                                                                    [Reporter]  ──▶  Manifest
                                                                                          │
                                                                                          ▼
                                                                                  RedactionResult
```

### 9.1 Pipeline function

```python
def redact(input: ImageInput, policy: Policy) -> RedactionResult: ...
```

Synchronous. The HTTP handler runs it in a threadpool
(`fastapi.concurrency.run_in_threadpool`) so the event loop stays
free.

### 9.2 Determinism (DT-001)

The pipeline contains no non-deterministic step in v0.1. The
canonical form for manifest equivalence is:

1. Sort `findings` by tuple `(rule_id, bbox.y, bbox.x, bbox.w, bbox.h, id)`.
2. Sort `warnings` by tuple `(source, code, message)`.
3. Exclude `created_at` from the canonical form (only present on
   the on-disk artefact).
4. Serialise as canonical JSON: `sort_keys=True`,
   `separators=(",", ":")`, no whitespace.
5. Hash with SHA-256 to produce the comparison key.

DT-001 asserts that two runs of TC-001 with the same input + same
policy produce byte-identical `output_image.bytes` and identical
manifest canonical-form hashes.

### 9.3 Error handling

Each stage raises a typed `RedactError` subclass. A single boundary
handler in `redact_ai.server.app` catches the base class and
converts to `ErrorEnvelope` + the HTTP status from §13.

Detector failures are **partial**: the registry catches the
exception, appends a `Warning` with `source="detector"`, and
continues with the remaining detectors (FR-8.2). All other failures
produce no output (ADR-005).

### 9.4 Memory hygiene

`Document` and `Findings` are released once `Redactor` and
`Reporter` have produced their outputs. The raw OCR text held in
`Token.text` is replaced with a sentinel string before the
`Document` goes out of scope; this is a best-effort hygiene step,
not a defence against a memory-reading adversary (out of scope per
`SECURITY_v0.1.md` §2.4).

No request body is written to disk by the pipeline. The user-chosen
output path is written by the **caller** (CLI or HTTP handler), not
by the pipeline function.

---

## 10. CLI Design

The v0.1 user-visible surface is the local web UI; the CLI is the
**bootstrapping command** that starts the server and opens the
browser.

### 10.1 Default invocation

```text
$ redact-ai
```

Behaviour:

1. Parse args.
2. Build `ServerConfig`.
3. Bind FastAPI on `127.0.0.1` with an ephemeral port (`port=0`).
4. Print the bound URL on `stderr` (e.g., `http://127.0.0.1:54321`).
5. `webbrowser.open(url)` — non-fatal if the browser fails to
   launch; the URL is still on stderr.
6. Block on Uvicorn's main loop until SIGINT.

### 10.2 Flags (v0.1)

| Flag | Default | Purpose |
| --- | --- | --- |
| `--port <int>` | `0` (ephemeral) | Override the port (still loopback-only). |
| `--no-browser` | `False` | Start the server but do not auto-open the browser. |
| `--policy <name\|path>` | `default` | Preload a non-default policy. |
| `--log-level` | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `--ocr-engine <paddle\|tesseract>` | `paddle` | Override OCR engine for this run. |
| `--version` | — | Print version + exit. |
| `--help` | — | Print usage + exit. |

### 10.3 Reserved subcommand

```text
$ redact-ai run --input ./screenshot.png …
```

Reserved for v0.2 per `API_SPEC_v0.1.md` §5. In v0.1, invoking
`run` prints `Available in v0.2; use the local web UI for v0.1.`
and exits with code `64` (`EX_USAGE`).

### 10.4 Console entrypoint

`pyproject.toml`:

```toml
[project.scripts]
redact-ai = "redact_ai.cli:main"
```

---

## 11. Performance Requirements

| NFR | Target | Enforcement in v0.1 |
| --- | --- | --- |
| NFR-1.1 | ≤ 3 s end-to-end for a 1080p screenshot (incl. localhost roundtrip) | `pytest-benchmark` test on a 1080p golden, asserts mean < 3.0 s |
| NFR-1.2 | ≤ 1 GB peak RAM | `tracemalloc` smoke test on the largest golden |
| NFR-1.3 | ≤ 2 s cold-start | Lazy-load PaddleOCR after the listener is bound; cold-start measured by time from process start to `200 OK` from `/healthz` |
| NFR-2.1 | Recall ≥ 95% on baseline | Computed against TC-001…TC-010 expected-findings table |
| NFR-2.2 | False-positive rate ≤ 5% | TC-006 (benign meme) must produce 0 findings |
| NFR-2.3 | 100% deterministic | DT-001 in `tests/e2e/test_determinism.py` |

**PaddleOCR cold-start handling.** PaddleOCR downloads model
weights on first use. For NFR-1.3 to be realistic, weights are
**pre-downloaded at install time** via a post-install step
documented in the README. The `/healthz` endpoint blocks (returns
`503`) until the OCR engine reports ready; the cold-start
benchmark waits for the first `200 OK`.

---

## 12. Edge Cases

| Edge case | Behaviour |
| --- | --- |
| Unsupported MIME (e.g., HEIC) | `E_INPUT_FORMAT`, HTTP 415, no output (TC-010) |
| Zero-byte upload | `E_INPUT_FORMAT`, HTTP 415 |
| Image larger than 25 MB | `E_INPUT_FORMAT` with hint "max 25 MB" (server-side limit) |
| Truncated / corrupt PNG | `E_INPUT_FORMAT`; the ingestor re-decodes via Pillow to detect |
| OCR returns empty `Document` | Pipeline succeeds; `manifest.stats.redactions_total = 0`; output image is binary-equivalent to input (TC-006-style) |
| Detector raises | Continue with remaining detectors; append `Warning(source="detector")` (FR-8.2) |
| Redactor post-condition fails | `E_REDACTION`, no output (ADR-005) |
| Low-confidence detection in `strict` | Redact + add `low_confidence` warning |
| Low-confidence detection in `lenient` | Skip + add `low_confidence_skipped` warning |
| Drag-drop on unsupported browser | `<input type=file>` fallback path is always present in the HTML |
| Cross-origin upload attempt | HTTP 403 with `E_POLICY` (server-policy: same-origin only) |
| Missing or invalid CSRF token | HTTP 403 with `E_POLICY` |
| Two redactions in flight | Pipeline is request-scoped; concurrent requests OK; PaddleOCR call serialised by a per-process lock |
| Browser launch fails | Server still runs; URL printed on `stderr` |
| `--port` already in use | If user supplied `--port` explicitly, fail with `E_IO`; else retry with another ephemeral port |
| OCR engine unavailable (PaddleOCR import error) | Fail-fast on startup with `E_IO` and a hint to `pip install redact-ai[ocr-tesseract]` and `--ocr-engine tesseract` |

---

## 13. Security & Privacy Model

Implementation-concrete restatement of `SECURITY_v0.1.md` §4a.

### 13.1 Bind address

`127.0.0.1` only. Passed as `host="127.0.0.1"` to Uvicorn. **Never**
`0.0.0.0` or any external interface. A startup hook asserts the
configured host equals `127.0.0.1` and exits with `E_POLICY`
otherwise.

### 13.2 Origin / Host validation (middleware)

Allowlist:

```python
ALLOWED_ORIGINS = {
    "http://127.0.0.1",
    "http://localhost",
    "http://[::1]",
}
```

The middleware extracts `Origin` (preferred) or falls back to
`Host`, normalises (strip trailing slash, lowercase host, strip
port for the comparison), and rejects anything outside the
allowlist with HTTP 403 + `ErrorEnvelope { code: "E_POLICY",
stage: "server" }`.

CORS is **not** enabled. Cross-origin requests are dropped by the
above middleware before they reach any route.

### 13.3 CSRF

A per-process token is generated at startup (`secrets.token_urlsafe(32)`)
and rendered into the static page as
`<meta name="csrf-token" content="...">`. On every `POST /redact`,
the client submits the token in a `csrf_token` form field. The
middleware compares it against the per-process token in constant
time (`hmac.compare_digest`). Mismatch → HTTP 403 + `E_POLICY`.

The token rotates whenever the server restarts. There is no
session table; the comparison is stateless against the
per-process value.

### 13.4 No auth, no persistence

Single-user, single-machine — no credentials. The server holds no
state between requests. Raw bytes are never written to disk. The
user-chosen output path is written by the HTTP handler **after**
the pipeline completes, only when the request body indicated an
explicit save target.

### 13.5 Logging hygiene

The `SafeFormatter` strips any record fields named `text`,
`matched_text`, or `bbox` (NFR-8.2). Structured fields surfaced to
logs: `stage`, `rule_id`, `policy_id`, `duration_ms`,
`request_id`. No raw image bytes ever enter the log path.

### 13.6 Manifest content

`matched_text` is included only when `policy.verbose_report = True`
(ADR-006). The reporter explicitly drops the field when the policy
disables it; this is enforced at write time, not just read time.

### 13.7 HTTP status mapping for the error envelope

| Code | HTTP status | Semantics |
| --- | --- | --- |
| `E_INPUT_FORMAT` | 415 Unsupported Media Type | MIME / size / corruption |
| `E_OCR` | 502 Bad Gateway | OCR engine failed (treat as upstream) |
| `E_DETECTOR` | 502 Bad Gateway | Detector failure that prevented output (after partial-tolerance per FR-8.2) |
| `E_REDACTION` | 500 Internal Server Error | Redactor post-condition failed; no output |
| `E_IO` | 500 Internal Server Error | Filesystem / port / engine-import failure |
| `E_POLICY` | 400 Bad Request | Policy-level rejection (CSRF, origin, validation), unless §13.2 / §13.3 specifies 403 |

§13.2 and §13.3 explicitly produce HTTP 403 even though the code is
`E_POLICY`; the table above documents the default mapping for any
other policy-level error.

### 13.8 Threats out of scope

Root-level adversaries, side-channel attacks, and tamper-resistant
audit logging are explicitly out of scope per
[`SECURITY_v0.1.md`](./SECURITY_v0.1.md) §2.4.

---

## 14. Folder Structure

```text
redact-ai/                              # repo root
├── pyproject.toml                      # project metadata, deps, console script
├── README.md
├── LICENSE
├── PROMPTS.md
├── docs/                               # existing v0.1 docs (unchanged)
│   ├── PRODUCT_v0.1.md
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
│   ├── TECH_STACK_OPTIONS_v0.1.md
│   ├── TECHNICAL_DESIGN_v0.1.md        # this file
│   ├── DECISIONS.md
│   ├── ROADMAP.md
│   └── CONTRIBUTING.md
├── redact_ai/                          # NEW v0.1 package
│   ├── __init__.py                     # re-exports public types
│   ├── types.py                        # all Pydantic models from §6
│   ├── ingestor.py
│   ├── ocr/
│   │   ├── __init__.py
│   │   ├── contract.py                 # OcrEngine Protocol + Hints + NormalisedImage
│   │   ├── paddle.py                   # PaddleOcrEngine (default)
│   │   └── tesseract.py                # TesseractOcrEngine (extras)
│   ├── detect/
│   │   ├── __init__.py
│   │   ├── contract.py                 # Detector Protocol + BaseDetector
│   │   ├── identity.py                 # ID-001..ID-005
│   │   ├── contact.py                  # CO-001..CO-003
│   │   ├── financial.py                # FI-001..FI-004 (incl. Luhn)
│   │   ├── credentials.py              # CR-001..CR-003
│   │   ├── health.py                   # HE-001 only in v0.1
│   │   ├── location.py                 # LO-001
│   │   └── registry.py                 # rule_id -> Detector lookup
│   ├── redact/
│   │   ├── __init__.py
│   │   ├── contract.py                 # Redactor Protocol
│   │   └── block.py                    # BlockRedactor
│   ├── report/
│   │   ├── __init__.py
│   │   └── manifest.py                 # Reporter + canonical_form()
│   ├── policy/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   └── builtins/
│   │       ├── default.json
│   │       └── strict.json
│   ├── server/
│   │   ├── __init__.py
│   │   ├── app.py                      # create_app()
│   │   ├── routes.py                   # /redact, /policies, /healthz, /
│   │   ├── middleware.py               # OriginHostValidator, CsrfValidator
│   │   └── static/
│   │       ├── index.html              # drag-drop page
│   │       ├── app.js
│   │       └── app.css
│   ├── pipeline.py                     # redact(input, policy) -> RedactionResult
│   ├── cli.py                          # `redact-ai` console entrypoint
│   ├── errors.py                       # typed exceptions + ErrorEnvelope mapper
│   └── logging.py                      # SafeFormatter + dictConfig
├── tests/
│   ├── unit/
│   │   ├── test_ingestor.py
│   │   ├── test_detectors_identity.py
│   │   ├── test_detectors_contact.py
│   │   ├── test_detectors_financial.py
│   │   ├── test_detectors_credentials.py
│   │   ├── test_redactor_block.py
│   │   ├── test_reporter_canonical.py
│   │   ├── test_policy_loader.py
│   │   ├── test_csrf.py
│   │   └── test_origin_validator.py
│   ├── integration/
│   │   ├── test_pipeline_paddle.py
│   │   ├── test_pipeline_tesseract.py
│   │   ├── test_security.py            # CSRF + origin/host together
│   │   └── test_http_roundtrip.py
│   ├── e2e/
│   │   ├── test_tc_001_bank_statement.py
│   │   ├── test_tc_002_email_thread.py
│   │   ├── test_tc_003_lab_report.py
│   │   ├── test_tc_004_id_photo.py
│   │   ├── test_tc_005_code_screenshot.py
│   │   ├── test_tc_006_benign_meme.py
│   │   ├── test_tc_007_dashboard.py
│   │   ├── test_tc_008_low_quality_phone.py
│   │   ├── test_tc_009_multilingual_receipt.py
│   │   ├── test_tc_010_unsupported_format.py
│   │   ├── test_determinism.py         # DT-001
│   │   ├── test_cli_bootstrap.py
│   │   └── test_cold_start.py          # NFR-1.3
│   ├── benchmarks/
│   │   └── test_latency_1080p.py       # NFR-1.1
│   └── assets/                         # synthetic goldens, no real PII
│       └── ...
└── .github/
    └── workflows/
        └── ci.yml
```

---

## 15. Engineering Risks

Risks specific to the **MVP build**. Distinct from the threat-model
risk table in [`SECURITY_v0.1.md`](./SECURITY_v0.1.md).

| Risk | Mitigation | Trigger to revisit |
| --- | --- | --- |
| `paddlepaddle` wheel availability gaps on Windows / arm64 | CI matrix tests both; documented Tesseract `[ocr-tesseract]` extras path with `--ocr-engine tesseract` | Three or more user-reported install failures in a release window |
| PaddleOCR model download adds first-run latency | Prefetch weights at install time via a documented post-install step; `/healthz` blocks until model is loaded | Cold-start exceeds NFR-1.3 in a fresh environment |
| First-run OS firewall prompt confuses users | README banner; loopback-only minimises surface area | Repeated user reports |
| OCR misses subtle PII (low-contrast or stylised) | Accuracy benchmark against the golden corpus; UI surfaces low-confidence regions; future migration to PaddleOCR-PP-OCRv4 if accuracy regresses | Recall < 95% on the benchmark |
| Pixel-zero post-condition false positive on lossy formats | Re-encode the redacted image in a lossless intermediate, then to the target format, with a final read-back verification | Test failure on a JPEG / WebP golden |
| Concurrent uploads exhaust memory | Per-process upload-size cap (25 MB); PaddleOCR call serialised by a `threading.Lock` | OOM observed under stress test |
| Drag-drop UI inconsistent across browsers | `<input type=file>` fallback is always rendered; tested on Chromium, Firefox, Safari | Drag-drop reliability blocks adoption |
| FastAPI / Uvicorn cold-start drift | Lazy-load OCR after the listener is bound; `/healthz` gates readiness | NFR-1.3 regression |
| `E_REDACTION` post-condition triggers spuriously on alpha channels | `BlockRedactor` flattens to RGB before sampling; alpha is restored on encode | Spurious `E_REDACTION` on PNG goldens |
| Policy JSON drift across versions | Manifests embed `policy_id` + `policy_version`; loader rejects unknown `rule_id`s with a clear error | A user reports a policy that won't load after upgrade |

---

## 16. Definition of Done (MVP)

A v0.1 release requires every line ticked. Criterion → proof
mapping (each "proof" is a CI-runnable test or check):

| # | Criterion | Proof |
| --- | --- | --- |
| 1 | Package installs cleanly on macOS / Linux / Windows × Python 3.11 / 3.12 | CI matrix green on `ubuntu-latest`, `macos-latest`, `windows-latest` |
| 2 | `redact-ai` console script starts the server and opens a browser | `tests/e2e/test_cli_bootstrap.py` |
| 3 | TC-001 … TC-010 all green | `tests/e2e/test_tc_*.py` |
| 4 | DT-001 (determinism) green | `tests/e2e/test_determinism.py` |
| 5 | Latency benchmark under 3 s on a 1080p golden | `tests/benchmarks/test_latency_1080p.py` |
| 6 | RAM peak under 1 GB on the largest golden | `tracemalloc` assertion in `test_latency_1080p.py` |
| 7 | Cold-start under 2 s to first `/healthz` 200 | `tests/e2e/test_cold_start.py` |
| 8 | `Origin` / `Host` validator rejects cross-origin and non-loopback requests | `tests/integration/test_security.py` |
| 9 | CSRF validator rejects missing or invalid tokens | same |
| 10 | Pixel-zero post-condition holds on every TC-* golden | `tests/unit/test_redactor_block.py` |
| 11 | Manifest excludes `matched_text` by default | `tests/unit/test_reporter_canonical.py` |
| 12 | Default policy is `strict`; both `default.json` and `strict.json` ship as package data | `tests/unit/test_policy_loader.py` |
| 13 | `README.md` documentation index links this TDD | `grep -n 'TECHNICAL_DESIGN_v0.1.md' README.md` |
| 14 | No real PII in any test asset, doc example, or built-in policy | `grep` check on test assets and Markdown |
| 15 | All four spec TODOs (`Hints`, `NormalisedImage`, `Policy`, `ErrorEnvelope`) are resolved by Pydantic stubs in this TDD | doc cross-reference (this file §6) |
