# examples/

Reference assets for `redact-ai`. Everything in this tree should be
**synthetic** — never include real user data.

## Subdirectories

- [`sample_inputs/`](./sample_inputs) — Example images and documents
  used as inputs to the pipeline.
- [`expected_outputs/`](./expected_outputs) — The corresponding
  redacted images and manifests we expect for each input.
- [`screenshots/`](./screenshots) — Illustrative screenshots used in
  documentation, blog posts, and demos.

## Conventions

- Pair every input with an expected output of the same base filename.
- Keep filenames lowercase, kebab-case, and descriptive
  (e.g. `bank-statement-001.png`).
- Store any per-file notes in a sibling `.md` file.

> TODO: Populate with curated samples once contributors are onboarded.
