# FUNCTIONAL REQUIREMENTS — redact-ai (v0.1)

> Status: Draft. This document enumerates the behaviours the system must
> exhibit. Each requirement has a stable ID for traceability with tests.

Conventions:

- **MUST** — required for v0.1 release.
- **SHOULD** — strongly desired for v0.1.
- **MAY** — optional, considered for later versions.

---

## FR-1. Input Handling

| ID | Requirement |
| --- | --- |
| FR-1.1 | The system **MUST** accept image inputs in PNG, JPEG, and WebP. |
| FR-1.2 | The system **MUST** validate the input is a supported format and reject otherwise with a clear error. |
| FR-1.3 | The system **MUST** strip EXIF metadata from the working copy of any input image. |
| FR-1.4 | The system **SHOULD** accept clipboard image input on supported platforms. |
| FR-1.5 | The system **MAY** accept multi-page PDF input *(deferred to v0.2)*. |

---

## FR-2. OCR & Layout Extraction

| ID | Requirement |
| --- | --- |
| FR-2.1 | The system **MUST** extract text content from the input image. |
| FR-2.2 | The system **MUST** record a bounding box for every recognised text fragment. |
| FR-2.3 | The system **MUST** preserve a stable reading order across the document. |
| FR-2.4 | The system **SHOULD** expose a confidence score per fragment. |

---

## FR-3. Detection

| ID | Requirement |
| --- | --- |
| FR-3.1 | The system **MUST** detect the entity types defined in [`REDACTION_RULES_v0.1.md`](./REDACTION_RULES_v0.1.md). |
| FR-3.2 | The system **MUST** assign every detection to a single, named entity category. |
| FR-3.3 | The system **MUST** allow detectors to be enabled/disabled via policy. |
| FR-3.4 | The system **SHOULD** return a confidence score with each finding. |
| FR-3.5 | The system **SHOULD** collapse overlapping findings into a single redaction region. |

---

## FR-4. Redaction

| ID | Requirement |
| --- | --- |
| FR-4.1 | The system **MUST** produce a redacted image where every identified region is visually masked. |
| FR-4.2 | The system **MUST** support at least one default redaction style (solid block). |
| FR-4.3 | The system **SHOULD** support multiple styles: solid block, blur, pixelate, label. |
| FR-4.4 | The system **MUST** preserve the original image dimensions and aspect ratio. |
| FR-4.5 | The system **MUST NOT** include any original sensitive pixels in the masked region of the output. |

---

## FR-5. Reporting

| ID | Requirement |
| --- | --- |
| FR-5.1 | The system **MUST** emit a structured redaction report. |
| FR-5.2 | The report **MUST** include category counts and bounding boxes for each redaction. |
| FR-5.3 | The report **MUST NOT** include the raw matched text by default. |
| FR-5.4 | The system **MAY** include matched text only when an explicit "verbose" flag is set by the user. |

---

## FR-6. Configuration

| ID | Requirement |
| --- | --- |
| FR-6.1 | The system **MUST** ship with at least one default policy. |
| FR-6.2 | The system **SHOULD** allow users to author and load custom policies. |
| FR-6.3 | Policies **MUST** be human-readable and version-controllable. |

---

## FR-7. Output

| ID | Requirement |
| --- | --- |
| FR-7.1 | The system **MUST** produce the redacted image in the same format as the input by default. |
| FR-7.2 | The system **SHOULD** allow the output format to be overridden. |
| FR-7.3 | The system **MUST NOT** overwrite the input file unless the user explicitly opts in. |

---

## FR-8. Failure Modes

| ID | Requirement |
| --- | --- |
| FR-8.1 | If OCR fails, the system **MUST** fail closed (no output produced) rather than emit unredacted content. |
| FR-8.2 | If a detector errors, the system **MUST** continue with the remaining detectors and surface the error in the report. |
| FR-8.3 | The system **MUST** never silently downgrade redactions. |

---

## FR-9. v0.1 Surface — Local Web UI

| ID | Requirement |
| --- | --- |
| FR-9.1 | The v0.1 entry surface **MUST** be a local web UI: a Python server bound to `127.0.0.1` plus a single static drag-and-drop page served from the same process. |
| FR-9.2 | The server **MUST NOT** bind to any non-loopback interface (`0.0.0.0`, LAN IPs, or otherwise). |
| FR-9.3 | The UI **MUST** accept image uploads via multipart form (`POST /redact`). |
| FR-9.4 | The redacted image **MUST** be returned in the same response cycle as the upload. |
| FR-9.5 | The redaction manifest **MUST** be retrievable from a separate endpoint or returned alongside the image (see [`API_SPEC_v0.1.md`](./API_SPEC_v0.1.md)). |
| FR-9.6 | The server **MUST** reject requests whose `Origin` or `Host` is not loopback. |
| FR-9.7 | The server **MUST NOT** persist user content beyond the lifetime of a single request, except for explicitly user-chosen output paths (FR-7.x). |

See ADR-007 in [`DECISIONS.md`](./DECISIONS.md).

---

## 10. Open Questions

- Should the system warn the user when confidence on critical entities is low? *(TODO)*
- How should the system express "I might have missed something"? *(TODO)*
