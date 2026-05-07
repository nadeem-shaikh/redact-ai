# API SPEC — redact-ai (v0.1)

> Status: Draft. Defines the external contract for `redact-ai`. The
> shape is technology-agnostic — the same contract can back a CLI, a
> library, or an HTTP service.

---

## 1. Surface Areas

| Surface | Audience | Status |
| --- | --- | --- |
| Library API | Embedders | v0.1 target |
| Local HTTP API + Web UI | End users (primary surface) | **v0.1 target** |
| CLI | Power users | v0.2 target |

---

## 2. Core Operation

```text
redact(input: ImageInput, policy: Policy) -> RedactionResult
```

- **Idempotent** for identical inputs and policies.
- **Pure** — no side effects beyond explicit output sinks.

---

## 3. Types (Technology-Agnostic)

### 3.1 `ImageInput`

```text
ImageInput
  ├── source     : "file" | "bytes" | "clipboard"
  ├── mime_type  : "image/png" | "image/jpeg" | "image/webp"
  ├── bytes      : opaque byte sequence (when source != "file")
  └── path       : filesystem path (when source == "file")
```

### 3.2 `Policy`

```text
Policy
  ├── id              : string
  ├── version         : semver string
  ├── detectors       : [DetectorRef]
  ├── redaction_style : "block" | "blur" | "pixelate" | "label"
  ├── strict          : boolean   (default: true)
  └── verbose_report  : boolean   (default: false)
```

### 3.3 `DetectorRef`

```text
DetectorRef
  ├── id          : string  (e.g. "FI-001")
  ├── enabled     : boolean
  ├── threshold   : "low" | "medium" | "high"
  └── overrides   : map<string, any>  (detector-specific config)
```

### 3.4 `RedactionResult`

```text
RedactionResult
  ├── output_image : ImageOutput
  ├── manifest     : Manifest
  └── warnings     : [Warning]
```

### 3.5 `ImageOutput`

```text
ImageOutput
  ├── mime_type : same as input by default
  ├── bytes     : opaque byte sequence
  └── path      : filesystem path (if persisted)
```

### 3.6 `Manifest`

```text
Manifest
  ├── policy_id        : string
  ├── policy_version   : semver string
  ├── input_hash       : sha256 of normalised input
  ├── created_at       : ISO 8601 timestamp
  ├── stats            : { redactions_total, by_category: {…} }
  └── findings         : [Finding]
```

### 3.7 `Finding`

```text
Finding
  ├── id           : string
  ├── category     : "IDENTITY" | "CONTACT" | …
  ├── rule_id      : string  (e.g. "CO-002")
  ├── bbox         : { x, y, w, h }  (pixel coords on the input)
  ├── confidence   : "low" | "medium" | "high"
  └── matched_text : string  (only when policy.verbose_report = true)
```

### 3.8 `Warning`

```text
Warning
  ├── code     : machine-readable identifier
  ├── message  : human-readable explanation
  └── source   : pipeline stage that produced the warning
```

---

## 4. Local HTTP API (v0.1 surface)

The v0.1 surface is a Python server bound to `127.0.0.1` plus a
single static drag-and-drop page served from the same process. The
HTTP API is local-only; security constraints are in
[`SECURITY_v0.1.md`](./SECURITY_v0.1.md) §4a.

### 4.1 Endpoints

| Method & Path | Purpose | Request | Response |
| --- | --- | --- | --- |
| `POST /redact` | Redact an uploaded image | `multipart/form-data` with `image`, optional `policy`, optional `style`, plus a CSRF token | Redacted image bytes (`image/<input-format>`) with `X-Redaction-Manifest-Url` header pointing at the manifest, **or** a JSON envelope `{ image: base64, manifest: Manifest }` when the client requests `Accept: application/json` |
| `GET /policies` | List built-in and user-loaded policies | — | JSON array of `{ id, version, description }` |
| `GET /healthz` | Liveness check for the local server | — | `200 OK` with `{ status: "ok", version }` |

### 4.2 Server Constraints

- **Bind address:** `127.0.0.1` only.
- **Origin / Host:** non-loopback values are rejected.
- **CSRF:** the upload page issues a per-session token; `POST /redact`
  validates it.
- **No auth:** the server is single-user, single-machine.
- **No persistence:** in-memory only; no request bodies are written
  to disk except for an explicit user-chosen output path.

These map to `FR-9.1`–`FR-9.7` in
[`FUNCTIONAL_REQUIREMENTS_v0.1.md`](./FUNCTIONAL_REQUIREMENTS_v0.1.md).

---

## 5. CLI Sketch (v0.2)

```text
$ redact-ai run \
    --input ./screenshot.png \
    --policy default \
    --output ./screenshot.redacted.png \
    --report ./screenshot.manifest.json
```

| Flag | Description |
| --- | --- |
| `--input` | Path to input image |
| `--policy` | Built-in name or path to a custom policy |
| `--output` | Destination path for redacted image |
| `--report` | Destination path for manifest |
| `--style` | Override redaction style |
| `--strict` | Toggle strict mode |
| `--verbose-report` | Include matched text in manifest *(use with caution)* |

---

## 6. Error Model

All errors are typed and carry a stable `code`:

| Code | Meaning |
| --- | --- |
| `E_INPUT_FORMAT` | Unsupported input format |
| `E_OCR` | OCR engine failed |
| `E_DETECTOR` | One or more detectors failed |
| `E_REDACTION` | Redactor could not produce a safe output |
| `E_IO` | Filesystem I/O failure |
| `E_POLICY` | Policy could not be loaded or validated |

The pipeline **MUST** fail closed: on any error that risks leaking
sensitive content, no output image is produced.

---

## 7. Versioning

- The contract follows **semver**.
- Breaking changes increment the major version.
- Manifests embed the policy and runtime versions for reproducibility.

---

## 8. Open Questions

- Should the manifest be signed by default? *(TODO)*
- Do we need a streaming variant for very large inputs? *(TODO)*
- How should custom policies be packaged and shared? *(TODO)*
