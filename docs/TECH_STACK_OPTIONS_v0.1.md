# TECH STACK OPTIONS — redact-ai (v0.1)

> Status: Draft. Compares viable tech-stack approaches for building
> `redact-ai`. The goal is to choose a stack that maximises **MVP
> velocity**, **OCR + PII detection accuracy**, **modularity**, and a
> credible **path to scale** — without sacrificing the project's
> privacy-first, local-first principles.

This document does **not** pick the final implementation language; it
narrows the field with explicit trade-offs so the team can commit with
confidence.

---

## Evaluation Criteria

| Criterion | Why it matters |
| --- | --- |
| MVP velocity | We need a working image redactor quickly, with minimal yak-shaving. |
| OCR & ML ecosystem | Detection accuracy depends on access to mature OCR + NER tooling. |
| Privacy posture | The default pipeline must run on-device; no telemetry of user content. |
| Modularity | Pipeline stages (ingest → OCR → detect → redact → report) must be replaceable. |
| Distribution | Easy to install for individual users; packageable for future surfaces. |
| Path to scale | Must extend to browser extension, desktop app, and (optional) API later. |
| Maintainer load | Small open-source project — keep operational complexity low. |

---

## Constraints from Existing ADRs

The following decisions are already made and recorded in
[`DECISIONS.md`](./DECISIONS.md). Any candidate stack **must**
satisfy all of them — they are not up for re-litigation here.

- **ADR-001** — *Image-first* is the v0.1 input modality. PDFs are
  v0.3.
- **ADR-002** — *Local-first by default*. The localhost loopback is
  considered on-device; no network egress in the default policy.
- **ADR-004** — *Modular pipeline* (Ingest → OCR → Detect → Redact
  → Report). Each stage must sit behind an explicit contract so
  individual components can be swapped without touching the others.
- **ADR-005** — *Fail closed on uncertainty.* On any error that
  risks leaking sensitive content, the pipeline produces no output.
- **ADR-007** — *v0.1 surface is a local web UI.* The v0.1
  user-visible entry point is a Python server bound to `127.0.0.1`
  + a single drag-and-drop HTML page.

These constraints rule out any stack that cannot host an in-process
HTTP server bound to the loopback interface, or that would require
exfiltrating user content to make detection work.

---

## Stack Options at a Glance

| # | Stack | One-line summary | Best for |
| --- | --- | --- | --- |
| A | **Python local-first** | Pragmatic ML-friendly local web UI on top of Python's mature OCR ecosystem. | **MVP (v0.1)** |
| B | **TypeScript / Node + WASM** | Single-language stack that scales naturally to a browser extension and Electron app. | Browser-first product strategy |
| C | **Rust core with FFI / WASM** | Performance- and privacy-maximalist core, embeddable everywhere. | Long-term privacy ceiling |
| D | **Hybrid: Python core + TS / Electron shell** | Python pipeline behind a TypeScript desktop UI; combines ML reach with product polish. | **Scaling (v1.0+)** |

---

## Option A — Python Local-First (Local Web UI Surface)

### A.1 Stack Description

| Layer | Choice |
| --- | --- |
| Language | Python 3.11+ |
| Packaging | `pyproject.toml` + `pipx` for end-user install |
| OCR | **PaddleOCR** as default per [ADR-008](./DECISIONS.md); Tesseract via `pytesseract` as an opt-in `[ocr-tesseract]` extras install for slim-footprint or `paddlepaddle`-unavailable environments |
| Layout / pre-processing | Pillow + OpenCV |
| Detection | Project-owned regex/dictionary detectors that map directly to the `redact-ai` rule IDs in [`REDACTION_RULES_v0.1.md`](./REDACTION_RULES_v0.1.md) |
| Redaction / rendering | Pillow for masking; configurable styles (block, blur, pixelate, label) |
| **v0.1 surface** | **FastAPI (or equivalent minimal framework) + a single static drag-and-drop HTML page**, served on `127.0.0.1` (see ADR-007) |
| CLI (v0.2) | Typer (Click under the hood) for ergonomic CLI |
| Configuration | YAML/TOML policy files validated with Pydantic |
| Testing | pytest, hypothesis, image diff tooling |

### A.1.1 Ingestion in Python (how the user actually hands over a screenshot)

A pure-Python MVP has four realistic ways to receive an image. Each
maps to a distinct UX moment in
[`UX_FLOW_v0.1.md`](./UX_FLOW_v0.1.md), Step 1.

| Entry point | How Python receives the bytes | UX feel | Cross-platform cost |
| --- | --- | --- | --- |
| **Local web UI** (FastAPI + drag-drop page) | Browser POSTs multipart to `127.0.0.1` | "Drag image, get redacted image back" — feels native everywhere | Easy; one extra process |
| Clipboard read | `Pillow.ImageGrab` (Win/macOS) or `wl-paste` / `xclip` shell-out (Linux) | Closest to the real moment — paste from screenshot tool | Cross-platform clipboard-image is uneven |
| Folder watcher | `watchdog` on `~/Screenshots` | Zero-touch but indirect | Easy |
| CLI + `--input <path>` | User passes a path | Power-user only | Trivial |

**v0.1 chooses the local web UI** as the primary surface (ADR-007 in
[`DECISIONS.md`](./DECISIONS.md)); the CLI ships as a v0.2 power-user
surface. Clipboard ingestion and folder watching are deferred to v0.2
once the per-OS code is justified.

### A.2 Pros

- **Fastest path to a working MVP.** Every pipeline stage has a mature, well-documented Python library.
- **Strong ML ecosystem available** *if and when* future detectors require it (spaCy, Hugging Face, transformers) — deliberately **not** pulled into the v0.1 baseline.
- **Excellent OCR options** — PaddleOCR is the v0.1 default for screenshot accuracy (per [ADR-008](./DECISIONS.md)); Tesseract is retained as a slim-footprint opt-in (`[ocr-tesseract]`).
- **Strong dev experience**: REPL-driven iteration on detection rules, rich notebook tooling.
- **Modular by default** — Python's import model maps cleanly to the pipeline contracts in `ARCHITECTURE_v0.1.md`.
- Friendly to AI coding agents — large training corpus available.

### A.3 Cons

- **Distribution friction.** The default install pulls `paddlepaddle` plus PaddleOCR weights (~500 MB–1 GB); native deps such as OpenCV further complicate single-binary distribution. The Tesseract-fallback path keeps a slimmer install available.
- **Performance ceiling.** Python is slower than Rust/Go for image-heavy pipelines; mitigated by C-backed libs.
- **No direct path to a browser extension** — would need a separate stack later.
- **Cold-start latency** can be noticeable on small inputs.
- Dependency surface area (numpy, opencv, etc.) is large; supply-chain hardening requires effort.

### A.4 Best Fit

- **Stage:** MVP (v0.1) and early v0.2.
- **When to choose:** You want to validate detection accuracy and UX quickly, and your primary distribution target is anyone with a browser — install is `pipx install redact-ai`, run is a single command that opens a localhost page.
- **When to avoid:** When the first surface you ship is a browser extension or sandboxed mobile app. (A future browser extension is a v0.4 concern; see [`ROADMAP.md`](./ROADMAP.md).)

---

## Option B — TypeScript / Node + WebAssembly

### B.1 Stack Description

| Layer | Choice |
| --- | --- |
| Language | TypeScript on Node.js 20+ |
| OCR | Tesseract.js (WASM build of Tesseract) |
| Image processing | `sharp` (libvips) for fast image ops |
| PII detection | Custom regex/dictionary engine + optional ONNX-runtime NER models |
| Layout / boxes | Tesseract.js bounding boxes; custom layout heuristics |
| CLI | `oclif` or `commander` |
| UI surface (future) | Browser extension (MV3) and/or Electron, sharing the same core |
| Configuration | JSON Schema validated policies |
| Testing | Vitest + image diff |

### B.2 Pros

- **One language across CLI, browser extension, desktop app.** Strong product story.
- **WASM OCR runs in the browser** — enables true client-side redaction for the future browser-extension surface.
- **Easy distribution** via npm and packaged binaries (`pkg`, `bun build`).
- **Mature async I/O** for batch flows and file watching.
- Vibrant ecosystem for desktop UI (Electron, Tauri-with-TS, web tech).

### B.3 Cons

- **Weaker ML ecosystem** vs. Python; advanced detectors require ONNX export and harder integration.
- **Tesseract.js is slower** than native Tesseract for large images, and PaddleOCR has no comparable WASM build today.
- **Less mature PII libraries** — most heavy lifting becomes project-owned code.
- Type-system + tooling churn (ESM/CJS, runtime choice) adds overhead.
- AI-friendly but not as well-supported by ML community examples.

### B.4 Best Fit

- **Stage:** When the first user-visible surface is a **browser extension** or **Electron app**, not a CLI.
- **When to choose:** You want one codebase to ship to the widest set of surfaces.
- **When to avoid:** If MVP success depends on top-tier OCR accuracy out of the box.

---

## Option C — Rust Core with FFI / WASM Bindings

### C.1 Stack Description

| Layer | Choice |
| --- | --- |
| Language | Rust (stable) |
| OCR | `ocrs` (Rust-native), or Tesseract via `leptess`/`tesseract-rs` |
| Image processing | `image`, `imageproc` |
| PII detection | Custom regex (`regex`) + small ONNX models via `ort` |
| CLI | `clap` |
| Cross-language | `pyo3` for Python bindings; WASM target for browser; `napi-rs` for Node |
| Configuration | `serde`-driven TOML/YAML policies |
| Testing | `cargo test` + golden-image diffs |

### C.2 Pros

- **Strongest privacy / safety story.** Memory-safe, easy to audit, single static binary.
- **Performance** — fastest end-to-end pipeline on a given laptop.
- **Best distribution model** — one self-contained binary per platform.
- **Re-use everywhere**: same core compiles to a CLI, a Python module, a Node addon, and WASM for the browser.
- Tiny attack surface compared with Python/Node dep trees.

### C.3 Cons

- **Slowest path to MVP.** OCR + PII detection components are far less mature than in Python.
- **Smaller ML ecosystem** — every advanced detector means custom integration.
- **Higher contributor barrier** — Rust expertise is rarer in OSS contributors.
- **Slower iteration** during early product discovery.
- WASM builds add cross-compilation toolchain complexity.

### C.4 Best Fit

- **Stage:** v1.0+ hardening, or as an embeddable core once the product shape is known.
- **When to choose:** When the project commits to maximum privacy guarantees and performance, and is willing to absorb slower early development.
- **When to avoid:** During MVP discovery, where iteration speed dominates.

---

## Option D — Hybrid: Python Core + TypeScript / Electron Shell

### D.1 Stack Description

| Layer | Choice |
| --- | --- |
| Pipeline | Python (as in Option A) |
| Inter-process boundary | Local subprocess + JSON-RPC over stdio (or named-pipe) |
| Desktop shell | Electron or Tauri with a TypeScript front-end |
| UI framework | React (or Svelte) + a minimal design system |
| Browser extension (future) | TypeScript front-end calling a local helper service |
| Packaging | Platform installers (pkg, dmg, msi) embedding the Python runtime |
| Telemetry | None by default, opt-in error reports only |

### D.2 Pros

- **Best of both worlds.** Keeps Python's ML reach behind a polished, cross-platform UI.
- **Clean separation of concerns** — UI, pipeline, and policies evolve independently.
- **Good product story** (drag-and-drop, review screen, copy-to-clipboard) without rewriting detection logic.
- Aligns with the modular contracts in `ARCHITECTURE_v0.1.md`.

### D.3 Cons

- **Two stacks to maintain** — more moving parts, two CI matrices.
- **Larger installers** (Python runtime + Chromium/Tauri shell).
- **More complex distribution** (signed installers, auto-update).
- IPC boundary needs careful design to keep sensitive content in-process.
- Higher onboarding cost for new contributors.

### D.4 Best Fit

- **Stage:** v1.0+ and beyond, once the pipeline is validated.
- **When to choose:** When the product shifts from "CLI for power users" to "drop-in app for everyone."
- **When to avoid:** During MVP — the two-stack overhead is not justified yet.

---

## Side-by-Side Comparison

| Dimension | A. Python | B. TypeScript | C. Rust | D. Hybrid |
| --- | --- | --- | --- | --- |
| MVP velocity | **High** | Medium | Low | Low |
| OCR maturity | **High** | Medium | Low | High |
| PII / NLP libraries | **High** | Low | Low | High |
| Performance | Medium | Medium | **High** | Medium |
| Privacy posture | High | High | **Highest** | High |
| Browser-extension path | Hard | **Easy** | Medium (via WASM) | Medium |
| Distribution | Medium | High | **Highest** | Medium |
| Install footprint | Medium | Low | **Lowest** | Higher |
| Contributor accessibility | **High** | High | Low | Medium |
| Maintenance overhead | Low | Low | Medium | **Higher** |

---

## Operational Considerations

These items are not stack-defining trade-offs — they are the
operational reality of shipping the recommended path. Captured here
so that an implementing engineer (or AI coding agent) does not have
to rediscover them.

### Dependency footprint

The v0.1 baseline is **PaddleOCR + Pillow + FastAPI +
project-owned regex/dictionary detectors** (per
[ADR-008](./DECISIONS.md)). PaddleOCR ships the `paddlepaddle`
runtime plus multilingual models (~500 MB–1 GB), accepted in
exchange for higher screenshot recall — the regime that dominates
real `redact-ai` inputs (anti-aliased UI text, low-DPI captures,
emoji). Tesseract is retained as an opt-in
`redact-ai[ocr-tesseract]` extras install for environments where
`paddlepaddle` is unavailable (notably some Windows / arm64
configurations) or where install footprint is the dominant
constraint.

NLP-based detectors (spaCy, transformer NER, hosted analyzer
frameworks) are **not** part of the v0.1 stack. They are
re-evaluated only when project-owned regex/dictionary detectors miss
too much against the golden corpus.

### Licensing

| Dependency | License |
| --- | --- |
| Tesseract | Apache 2.0 |
| PaddleOCR (optional) | Apache 2.0 |
| Pillow | HPND |
| OpenCV | Apache 2.0 |
| FastAPI / Starlette | MIT |
| Pydantic | MIT |
| Typer (v0.2 CLI) | MIT |

All compatible with the project's MIT licence. Recorded here for
due-diligence purposes.

### Install footprint (Option A baseline)

- `pipx install redact-ai` ≈ **500 MB–1 GB** with PaddleOCR
  (default per [ADR-008](./DECISIONS.md)) + Pillow + FastAPI +
  project detectors.
- `pipx install 'redact-ai[ocr-tesseract]'` ≈ **50–80 MB** for the
  Tesseract-only fallback (a system Tesseract install is required
  separately).
- The default install carries **no NLP/transformer dependencies**.

### CI matrix

The supported platform matrix is **macOS, Linux, and Windows**
(NFR-7.x). Per-platform notes:

- **PaddleOCR** depends on `paddlepaddle` wheels, which lag on
  Windows and some arm64 configurations; the CI matrix tests both
  the PaddleOCR default and the Tesseract fallback path
  (`pip install redact-ai[ocr-tesseract]` plus
  `--ocr-engine tesseract`).
- **Tesseract** (fallback path) install differs per platform
  (Homebrew / apt / chocolatey); document the install steps in
  `CONTRIBUTING.md`.
- **Pillow** ships pre-built wheels on all three platforms.
- **FastAPI / uvicorn** are pure-Python and portable.
- The **localhost web UI** must be smoke-tested per platform — first
  run can trigger an OS firewall prompt even on the loopback
  interface, and `Origin` / `Host` validation can behave differently
  across browsers.

---

## Final Recommendation

### MVP (v0.1) — **Option A: Python local-first, served via a local web UI**

**Reasoning**

1. **Velocity.** Python lets us ship a credible image-redaction pipeline in days, not weeks. PaddleOCR + Pillow + project-owned regex/dictionary detectors give us a working baseline with minimal custom code (engine choice per [ADR-008](./DECISIONS.md)).
2. **Detection quality.** The richest OCR and PII tooling lives in Python. Accuracy is the riskiest variable for `redact-ai`; we want the strongest libraries on day one.
3. **Right surface for non-CLI users.** A FastAPI server bound to `127.0.0.1` plus a single drag-and-drop page gives every user a familiar canvas (their browser) without compromising local-first (ADR-002 / ADR-007).
4. **Modularity.** The architecture's pipeline boundaries map cleanly to Python modules and adapter contracts, making future swaps (PaddleOCR, custom detectors) low-cost.
5. **Local-first preserved.** The localhost loopback is on-device; no network calls in the default policy.
6. **Contributor friendliness.** Python is the most common contributor language for ML-adjacent OSS projects, lowering the barrier to participation and making the codebase highly approachable to AI coding agents.

We accept the trade-off that the **browser extension** is not a v0.1 surface and the **CLI** ships as a v0.2 power-user tool, not a v0.1 primary entry point.

### Scaling (v1.0+) — **Option D: Python core + TypeScript / Electron shell**

**Reasoning**

1. **Re-use the validated pipeline.** Once detection quality and the policy model are proven in v0.1, we keep the Python core and put a polished UI in front of it instead of rewriting.
2. **Reach a non-CLI audience.** Most users will not install a CLI; an Electron/Tauri desktop app is the natural next surface, with a browser-extension companion driven by the same TypeScript front-end.
3. **Modularity preserved.** The IPC boundary between UI and pipeline is a feature, not a tax — it lets us harden the pipeline (sandbox, signed builds) independently of the UI.
4. **Clear migration path.** Heavy detectors can later be ported to **Rust (Option C)** behind the same pipeline contracts if performance or privacy demands it, without touching the UI.

### Migration: v0.1 (A) → v1.0+ (D)

Today's v0.1 surface is already a stepping stone toward Option D —
not a throwaway. The local web UI is a Python process that serves a
single HTML page over `127.0.0.1`. The v1.0+ desktop app does the
same thing inside a Tauri or Electron shell:

- The **HTML page** becomes the desktop shell's renderer with no
  rewrite — same drag-drop, same review screen.
- The **FastAPI handlers** (`POST /redact`, `GET /policies`,
  `GET /healthz`) become the JSON-RPC handlers on the IPC boundary
  between the shell and the embedded Python pipeline.
- The **Python pipeline itself is unchanged.** Ingestor, OCR,
  Detector, Redactor, and Report keep their contracts; only the
  surface in front of them swaps.

This means v0.1 quality work on policies, detectors, and the OCR
adapter is *directly* re-used in v1.0+ — not rewritten. The same
property holds for a future browser-extension surface (v0.4) that
talks to a local helper service rather than reimplementing the
pipeline.

### When to revisit

| Trigger | Likely move |
| --- | --- |
| Browser extension becomes the priority | Lift the detection rules into TS (Option B) and call a local helper for OCR |
| Detection latency becomes a UX blocker | Port hot path to Rust (Option C) and call from Python via `pyo3` |
| Enterprise / regulated deployment requested | Audit and harden Option D; consider signed Rust core for the pipeline |

---

## Risk Register (Recommended Path)

Risks specific to **shipping Option A as the v0.1 surface**, with
their mitigations and the conditions that should prompt a re-think.
This register is scoped to stack-and-distribution risk; it
**complements**, rather than replaces, the threat-model risk table
in [`SECURITY_v0.1.md`](./SECURITY_v0.1.md).

| Risk | Mitigation | Trigger to revisit |
| --- | --- | --- |
| OCR accuracy varies by image quality | Golden test corpus per [`TEST_CASES_v0.1.md`](./TEST_CASES_v0.1.md); per-finding confidence in the manifest | Recall on baseline corpus drops below 95% |
| Python packaging on Windows is fragile | CI matrix tests wheels per platform; documented workarounds; bundle `paddlepaddle` (default) and Tesseract (fallback) install hints in `CONTRIBUTING.md` | Three or more user-reported install failures in a release window |
| Heavy default OCR deps inflate supply-chain risk | Pin + hash; PaddleOCR is the default per [ADR-008](./DECISIONS.md); Tesseract retained as an opt-in `[ocr-tesseract]` extras install for slim-footprint or `paddlepaddle`-unavailable environments | User reports of `paddlepaddle` install failures, supply-chain concerns, or NFR-2.1 met by Tesseract on the curated corpus within a meaningful margin |
| Localhost server mistaken for cloud SaaS | README banner + UI footer ("Everything runs on your machine"); no telemetry endpoints in the binary | User confusion in support / community channels |
| Browser drag-drop UX inconsistent across browsers | Ship multipart upload first; drag-drop on top; clipboard paste later (v0.2) | Drag-drop reliability issues block adoption |
| FastAPI startup overhead noticeable on cold launch | Lazy-load OCR + detectors after the server is bound | Cold-start latency exceeds the 3 s end-to-end budget (NFR-1.1) |

---

## Open Questions

- Do we lock to a single Python version or support a window? *(TODO)*
- Should the v0.1 default policy be "strict" or "lenient"? *(TODO)*
- When does it make sense to add a thin Rust performance core behind the Python facade? *(TODO)*
