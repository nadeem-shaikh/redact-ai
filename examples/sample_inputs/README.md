# sample_inputs/

Synthetic input artefacts used to exercise the redaction pipeline.

## Rules

- **Synthetic only.** No real names, IDs, or numbers.
- Prefer images that map to test cases in
  [`../../docs/TEST_CASES_v0.1.md`](../../docs/TEST_CASES_v0.1.md).
- Name files to match their test case where possible:
  `tc-001-bank-statement.png`, `tc-002-email-thread.png`, etc.

## File Layout

```text
sample_inputs/
├── tc-001-bank-statement.<ext>
├── tc-002-email-thread.<ext>
├── tc-003-medical-lab-report.<ext>
└── ...
```

> TODO: Add curated sample inputs.
