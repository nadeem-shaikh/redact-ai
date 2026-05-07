# expected_outputs/

Expected redaction artefacts for the inputs in
[`../sample_inputs/`](../sample_inputs).

## Conventions

- Pair every input file with an expected redacted output of the same
  base name plus a `.redacted` infix.
- Each output **MAY** be accompanied by an expected manifest in JSON
  with the same base name plus `.manifest.json`.

## File Layout

```text
expected_outputs/
├── tc-001-bank-statement.redacted.<ext>
├── tc-001-bank-statement.manifest.json
├── tc-002-email-thread.redacted.<ext>
├── tc-002-email-thread.manifest.json
└── ...
```

## Manifest Equivalence

When comparing actual vs expected manifests in tests, ignore fields
that are inherently non-deterministic (e.g. `created_at`). See
[`../../docs/TEST_CASES_v0.1.md`](../../docs/TEST_CASES_v0.1.md).

> TODO: Add curated expected outputs once sample inputs exist.
