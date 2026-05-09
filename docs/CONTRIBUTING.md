# CONTRIBUTING — redact-ai

> Status: Draft. Guidelines for human and AI contributors.

Thanks for your interest in `redact-ai`! This project is in its
**documentation phase**, so most contributions today are about clarity,
correctness, and design rather than code.

---

## 1. How You Can Help

- **Improve the docs.** Fix unclear wording, add missing edge cases,
  flag broken assumptions.
- **Propose redaction rules.** Suggest entity types we should recognise
  (with examples and locale notes).
- **Stress-test the design.** File issues describing situations the
  current architecture would handle poorly.
- **Contribute synthetic test assets.** Build out the
  [`examples/`](../examples) corpus with realistic but **synthetic**
  inputs.

---

## 2. Project Principles

Please read these before contributing:

1. **Privacy first.** Never propose features that weaken local-first or
   no-telemetry guarantees.
2. **Image-first.** Designs should treat screenshots and images as the
   primary input.
3. **Technology-agnostic.** Avoid prescribing a specific framework or
   model in shared documents.
4. **Modularity.** Prefer changes that strengthen pipeline component
   boundaries.

---

## 3. Working With AI Coding Agents

This repository is structured to be **AI-friendly**. When delegating to
an AI agent:

- Point the agent at the relevant `_v0.1` doc.
- Ask the agent to honour the contracts in
  [`API_SPEC_v0.1.md`](./API_SPEC_v0.1.md).
- Require the agent to update [`DECISIONS.md`](./DECISIONS.md) for any
  architectural choice it makes.
- Require the agent to leave a `TODO` whenever it skips a detail rather
  than inventing one.

---

## 4. Issue Workflow

1. **Search first.** Check open and closed issues for duplicates.
2. **Open an issue** before significant changes; align on direction.
3. Use these labels where applicable:
   - `docs`, `architecture`, `rules`, `security`, `ux`, `good-first-issue`.
4. Reference the relevant document IDs (e.g. `FR-3.4`) in the issue.

---

## 5. Pull Request Workflow

This repository uses an **integration branch model**:

- `main` — release-quality, tagged.
- `dev` — the integration branch where v0.1 work lands first.
- short-lived feature branches off `dev` for individual changes.

Step-by-step:

1. Fork the repository (or, for maintainers, branch directly).
2. Create a topic branch off `dev` using one of:
   - `feat/<short-description>` for implementation work.
   - `docs/<short-description>` or `proposal/<short-description>`
     for documentation and design proposals.
   - `feat/mvp-mN-<slug>` for milestone PRs against the
     [`MVP_BUILD_SPEC_v0.1.md`](./MVP_BUILD_SPEC_v0.1.md)
     milestones.
3. Keep PRs focused — one document or one cohesive idea per PR.
4. Open the PR with `base = dev`. Promotion from `dev → main`
   happens on releases via a separate PR by maintainers.
5. Update [`DECISIONS.md`](./DECISIONS.md) when proposing
   architectural changes.
6. Ensure markdown renders cleanly and links resolve.

---

## 6. Style Guide

- Markdown files use ATX headings (`#`, `##`, …).
- Lines wrap at ~80 characters where practical.
- Prefer tables for enumerations.
- Use sentence case for headings.
- Use stable IDs (`FR-2.1`, `CO-002`, etc.) when referencing
  requirements or rules.

---

## 7. Code of Conduct

We aim to maintain a welcoming, professional environment. By
contributing you agree to act with empathy and respect.

> TODO: Adopt and link a formal Code of Conduct (e.g. Contributor
> Covenant).

---

## 8. Licensing

By contributing you agree your contributions are licensed under the
project's [MIT License](../LICENSE).

---

## 9. Getting Help

- File an issue with the `question` label.
- Reference the closest relevant document — it speeds up the discussion.

---

## 10. Local development setup

The v0.1 implementation milestones in
[`MVP_BUILD_SPEC_v0.1.md`](./MVP_BUILD_SPEC_v0.1.md) require
Tesseract on contributors' machines for the optional
`[ocr-tesseract]` extras path (PaddleOCR is the default and is
installed by `pip`). Install commands by platform:

| Platform | Install command |
| --- | --- |
| Linux (Debian / Ubuntu) | `sudo apt-get update && sudo apt-get install -y tesseract-ocr` |
| Linux (Fedora) | `sudo dnf install -y tesseract` |
| macOS (Homebrew) | `brew install tesseract` |
| Windows (Chocolatey) | `choco install -y tesseract` |
| Windows (Scoop) | `scoop install tesseract` |

After installing the binary, install the project with both
extras for development:

```text
pip install -e ".[dev,ocr-tesseract]"
```

The CI matrix mirrors these exact commands; see
[`MVP_BUILD_SPEC_v0.1.md`](./MVP_BUILD_SPEC_v0.1.md) §6.
