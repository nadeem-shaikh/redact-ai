# TEST CASES — redact-ai (v0.1)

> Status: Draft. A curated set of realistic example inputs and the
> expected behaviour. Each case is designed to be implementable as an
> automated test once code exists.

Conventions:

- Each case has a stable `TC-NNN` identifier.
- Inputs and outputs are described abstractly. Concrete sample assets
  live under [`../examples/`](../examples).
- All sample data is **synthetic**. Never use real user data.

---

## TC-001 — Bank statement screenshot

| Field | Value |
| --- | --- |
| Input | A screenshot of a bank statement showing account holder name, account number, IBAN, and three transactions. |
| Expected detections | `ID-001` (name), `FI-002` (IBAN), `FI-003` (account number) |
| Expected output | All three regions covered with the default redaction style; transactions remain visible. |
| Manifest stats | `IDENTITY: 1`, `FINANCIAL: 2` |

---

## TC-002 — Email thread screenshot

| Field | Value |
| --- | --- |
| Input | A screenshot of an email thread including subject line, sender/recipient addresses, and a phone number in the signature. |
| Expected detections | `CO-001` (emails), `CO-002` (phone) |
| Expected output | Email addresses and phone redacted; subject and body text preserved. |
| Manifest stats | `CONTACT: ≥ 2` |

---

## TC-003 — Medical lab report

| Field | Value |
| --- | --- |
| Input | A scanned lab report with patient name, date of birth, MRN, and lab values. |
| Expected detections | `ID-001`, `ID-002`, `HE-001` |
| Expected output | Identifying header redacted; lab values preserved for analysis. |
| Manifest stats | `IDENTITY: 2`, `HEALTH: 1` |

---

## TC-004 — Government ID card photo

| Field | Value |
| --- | --- |
| Input | A photo of a synthetic ID card with name, DOB, ID number, and photo. |
| Expected detections | `ID-001`, `ID-002`, `ID-003` |
| Expected output | All textual identifiers masked. *(Photo redaction is out of scope for v0.1.)* |
| Manifest stats | `IDENTITY: ≥ 3` |
| Notes | Add a warning indicating the photo region was not redacted. |

---

## TC-005 — Code editor screenshot with credentials

| Field | Value |
| --- | --- |
| Input | A screenshot of a code editor showing an AWS access key and a JWT in source. |
| Expected detections | `CR-003` (AWS key), `CR-001` (JWT) |
| Expected output | Both literals masked; surrounding code remains readable. |
| Manifest stats | `CREDENTIALS: ≥ 2` |

---

## TC-006 — Benign meme

| Field | Value |
| --- | --- |
| Input | A meme image with caption text but no sensitive content. |
| Expected detections | None |
| Expected output | Image is unchanged or trivially re-encoded with no redactions. |
| Manifest stats | `redactions_total: 0` |
| Notes | Validates the false-positive rate target in `NFR-2.2`. |

---

## TC-007 — Mixed-content dashboard

| Field | Value |
| --- | --- |
| Input | A screenshot of an analytics dashboard with user emails listed in a table. |
| Expected detections | `CO-001` for each row |
| Expected output | Email column masked; chart visuals untouched. |
| Manifest stats | `CONTACT: ≥ N` (N = number of rows) |

---

## TC-008 — Low-quality phone photo

| Field | Value |
| --- | --- |
| Input | A blurry phone photo of a printed letter with a name and postal address. |
| Expected detections | `ID-001`, `CO-003` (with `LOW` confidence) |
| Expected output | Name and address masked; warning emitted about confidence. |
| Manifest stats | `IDENTITY: 1`, `CONTACT: 1` |

---

## TC-009 — Multi-language receipt

| Field | Value |
| --- | --- |
| Input | A bilingual receipt (e.g. English + Spanish) with a card number. |
| Expected detections | `FI-001` (Luhn-valid PAN) |
| Expected output | Card number masked; receipt remains readable in both languages. |
| Manifest stats | `FINANCIAL: 1` |
| Notes | Verifies locale-agnostic detection of structured numbers. |

---

## TC-010 — Empty input / unsupported format

| Field | Value |
| --- | --- |
| Input | A zero-byte file or unsupported format (e.g. `.bmp`). |
| Expected behaviour | Pipeline rejects with `E_INPUT_FORMAT`; no output produced. |
| Manifest stats | n/a |
| Notes | Validates fail-closed behaviour from `FR-8.1`. |

---

## Determinism Tests

- **DT-001** — Re-running TC-001 with the same policy produces a
  byte-identical redacted image and an equivalent manifest.

---

## Open Questions

- How should we measure "equivalent manifest"? (timestamps differ) *(TODO)*
- Do we ship a community-contributed test corpus? *(TODO)*
- How are sample assets licensed? *(TODO)*
