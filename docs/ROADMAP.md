# ROADMAP — redact-ai

> Status: Living document. Tracks themes, milestones, and approximate
> ordering. Dates are intentionally omitted until the team forms.

---

## v0.1 — Foundation (current)

**Theme:** Documentation-first scaffolding.

- [x] Repository structure
- [x] Product vision and MVP scope
- [x] Architecture and data-flow design
- [x] Functional and non-functional requirements
- [x] Baseline redaction rule set
- [x] OCR pipeline contract
- [x] API specification
- [x] Security and threat model
- [x] Test-case catalogue
- [x] UX flow walkthrough
- [x] Contribution guide and ADR template

---

## v0.2 — Image MVP

**Theme:** First working release for screenshots and images.

- [ ] Reference implementation of the OCR adapter contract
- [ ] Baseline detectors for `IDENTITY`, `CONTACT`, `FINANCIAL`,
      `CREDENTIALS`
- [ ] Default policy and "strict" policy
- [ ] Solid-block redactor
- [ ] CLI entry point
- [ ] Manifest / report generator
- [ ] End-to-end tests covering `TC-001` through `TC-010`

---

## v0.3 — Documents

**Theme:** Multi-page and structured document support.

- [ ] PDF input (multi-page)
- [ ] Layout-aware redaction (tables, forms)
- [ ] Reading-order preservation across columns

---

## v0.4 — Integrations

**Theme:** Meet users where they already are.

- [ ] Browser extension (clipboard hand-off)
- [ ] OS-level share-sheet integration
- [ ] Desktop app shell

---

## v0.5 — Custom Rules

**Theme:** Make the system expressive for organisations.

- [ ] User-defined regex / dictionary detectors
- [ ] Policy authoring tooling
- [ ] Policy validation / linting

---

## v1.0 — Production Hardening

**Theme:** Trustworthy, signed, audited release.

- [ ] Reproducible builds
- [ ] Signed binaries / SBOMs
- [ ] Public benchmark suite
- [ ] Independent security review
- [ ] Documentation polish

---

## Beyond v1.0 (Speculative)

- Audio and video redaction
- Plugin marketplace for domain-specific detectors
- Encrypted on-device policy storage
- Optional cloud-assisted detectors with strict consent UX

---

## Status Legend

- [ ] Planned
- [x] Done
- [~] In progress
- [!] At risk

> TODO: Add quarter-level targets once contributor capacity is known.
