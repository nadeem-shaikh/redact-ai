# REDACTION RULES — redact-ai (v0.1)

> Status: Draft. Defines what counts as "sensitive information" for the
> baseline policy. Each rule has a stable ID, a category, and an example.

---

## 1. Rule Schema

Each rule is described as:

```text
ID         : Stable identifier
Category   : High-level grouping
Description: What this rule catches
Examples   : Realistic illustrations
Default    : Whether enabled by default
Notes      : Caveats, edge cases, locale variations
```

---

## 2. Categories

| Category | Description |
| --- | --- |
| `IDENTITY` | Names, dates of birth, government identifiers |
| `CONTACT` | Phone numbers, email addresses, postal addresses |
| `FINANCIAL` | Card numbers, IBAN, account numbers |
| `HEALTH` | Medical record numbers, diagnoses, prescriptions |
| `CREDENTIALS` | API keys, tokens, passwords |
| `LOCATION` | Coordinates, plate numbers, location-revealing artefacts |
| `CUSTOM` | User-defined rules |

---

## 3. Baseline Rules

### 3.1 Identity

| ID | Description | Example | Default |
| --- | --- | --- | --- |
| ID-001 | Full personal names | `Aanya Sharma` | On |
| ID-002 | Date of birth | `12 / 04 / 1992` | On |
| ID-003 | Government ID numbers (generic) | `XXXX-XXXX-XXXX` | On |
| ID-004 | Passport numbers (locale-aware) | `M1234567` | On |
| ID-005 | Driver's licence numbers | locale-specific | On |

### 3.2 Contact

| ID | Description | Example | Default |
| --- | --- | --- | --- |
| CO-001 | Email addresses | `name@example.com` | On |
| CO-002 | Phone numbers (international) | `+1 555 123 4567` | On |
| CO-003 | Postal addresses (multi-line) | `221B Baker Street, …` | On |

### 3.3 Financial

| ID | Description | Example | Default |
| --- | --- | --- | --- |
| FI-001 | Card numbers (PAN, with Luhn check) | `4111 1111 1111 1111` | On |
| FI-002 | IBAN | `GB29 NWBK 6016 1331 9268 19` | On |
| FI-003 | Generic bank account numbers | locale-specific | On |
| FI-004 | CVV / expiry pairs adjacent to a PAN | `09/27 123` | On |

### 3.4 Health

| ID | Description | Example | Default |
| --- | --- | --- | --- |
| HE-001 | Medical record numbers | `MRN: 0001234` | On |
| HE-002 | Common diagnosis codes | `ICD-10: E11.9` | Off |
| HE-003 | Prescription details | `Rx: Metformin 500mg` | Off |

### 3.5 Credentials

| ID | Description | Example | Default |
| --- | --- | --- | --- |
| CR-001 | Generic high-entropy tokens | `sk_live_…` | On |
| CR-002 | SSH private keys (block markers) | `-----BEGIN OPENSSH PRIVATE KEY-----` | On |
| CR-003 | Common cloud key prefixes | `AKIA…`, `AIza…` | On |

### 3.6 Location

| ID | Description | Example | Default |
| --- | --- | --- | --- |
| LO-001 | GPS coordinates | `37.4220° N, 122.0841° W` | On |
| LO-002 | Vehicle registration plates (visual) | image-based detection | Off |

### 3.7 Custom

| ID | Description | Example | Default |
| --- | --- | --- | --- |
| CU-001 | User-defined regex / dictionary detector | n/a | Off |

### 3.8 ML Engine (optional)

| ID | Description | Example | Default |
| --- | --- | --- | --- |
| ML-001 | GLiNER generalist PII engine (transformer NER, all categories) | any PII span | Off |

`ML-001` is an optional, opt-in engine that ships in the `redact-ai[strong]`
extra and complements the deterministic rules above (see
[ADR-013](./DECISIONS.md) and
[`DETECTORS_v0.1.md`](./DETECTORS_v0.1.md#ml-001--gliner-strong-pii-engine-optional)).
Its findings carry a per-finding category from the label→category map, so they
flow through the same merge / confidence / manifest path as any other rule.

> **Authoritative rule set:** this catalog is the v0.1 baseline. Rules added
> after it was frozen (ID-006 statistical name NER, ID-007 face detection,
> ID-008 payment-recipient names, FI-005 masked account numbers, and ML-001)
> are specified in [`DETECTORS_v0.1.md`](./DETECTORS_v0.1.md) and their ADRs,
> which are the source of truth for the current registry.

---

## 4. Detection Strategy Notes

- Each rule **MAY** combine regex, dictionary lookups, layout cues, and ML
  models. The contract is the same: emit findings with bounding boxes.
- Rules **MUST** be locale-aware where applicable, with a clear default
  locale (`en-US` for v0.1).
- Detectors **SHOULD** prefer **higher recall** by default — false
  positives are a UX concern, false negatives are a safety concern.

---

## 5. Confidence Levels

| Level | Meaning | Default Action |
| --- | --- | --- |
| `HIGH` | Strong evidence (e.g. checksum-passing PAN) | Redact |
| `MEDIUM` | Pattern matches but no checksum | Redact |
| `LOW` | Heuristic match only | Redact in "strict" policy; flag in "lenient" policy |

---

## 6. Open Questions

- How do we handle handwritten content? *(TODO)*
- Should non-Latin scripts ship in v0.1 or v0.2? *(TODO)*
- How do we surface culturally specific identifiers (e.g. national IDs
  across countries)? *(TODO)*
