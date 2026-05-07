# OCR PIPELINE — redact-ai (v0.1)

> Status: Draft. Describes how raw images are converted into a structured
> document model that detectors can operate on. Engine-agnostic by design.

---

## 1. Goals

- Produce a **layout-preserving** document model from any input image.
- Be **decoupled** from any specific OCR engine.
- Provide **stable identifiers** for every text fragment so findings can
  be traced back to pixels.

---

## 2. Stages

```text
Raw Image
    │
    ▼
[ Pre-process ] ── normalisation, deskew, denoise
    │
    ▼
[ Detect Regions ] ── identify text-bearing regions
    │
    ▼
[ Recognise ] ── OCR per region
    │
    ▼
[ Compose ] ── reading order, blocks, lines, words
    │
    ▼
Document Model  →  consumed by Detector Engine
```

---

## 3. Document Model

The canonical output of the OCR pipeline. Hierarchical and
self-contained:

```text
Document
  └── Pages[]
        └── Blocks[]
              └── Lines[]
                    └── Tokens[]
                          ├── text
                          ├── bbox  (x, y, w, h, page-relative)
                          ├── confidence (0.0–1.0)
                          └── id
```

Invariants:

- Every node has a stable `id` derived from its position + content hash.
- Coordinates are in **pixel units** of the post-pre-processing image.
- Reading order is a left-to-right, top-to-bottom traversal unless the
  layout module overrides it (e.g. multi-column).

---

## 4. Engine Adapter Contract

Any OCR engine plugged in **MUST** implement:

```text
recognise(image: NormalisedImage, hints: Hints) -> Document
```

- Input: a normalised image and optional hints (language, orientation).
- Output: a `Document` conforming to §3.
- Errors: typed and recoverable; the pipeline must continue on a
  per-region basis where possible.

> TODO: Define `Hints` and `NormalisedImage` schemas in
> [`API_SPEC_v0.1.md`](./API_SPEC_v0.1.md).

---

## 5. Pre-processing

The pre-processor **MAY** apply any of:

- Colour-space conversion (grayscale where appropriate)
- Deskew up to ±15°
- Denoise / contrast enhancement
- Up-sampling for low-resolution input
- DPI normalisation

The pre-processor **MUST NOT** crop content.

---

## 6. Reading Order & Layout

- Single-column documents: top-to-bottom, left-to-right.
- Multi-column: detected via whitespace projection or layout model.
- Tables: cells are blocks; rows preserved.
- Forms: label–value pairs preserved as adjacent blocks where possible.

---

## 7. Confidence Handling

- Token-level confidences propagate up to lines and blocks.
- Detectors may reject low-confidence tokens, *but* the redactor
  **SHOULD** err on the side of redaction when in doubt.

---

## 8. Failure Modes

| Failure | Behaviour |
| --- | --- |
| Engine cannot read image | Return error; pipeline fails closed |
| Engine returns partial output | Keep partial; mark missing regions |
| Pre-processor fails | Fall back to raw image; record warning |

---

## 9. Open Questions

- Should we standardise on a single document-model serialisation (JSON,
  Protobuf, etc.)? *(TODO)*
- How do we handle right-to-left scripts in reading order? *(TODO)*
- How are hand-drawn / mixed text+graphic regions represented? *(TODO)*
