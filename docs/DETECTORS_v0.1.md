# DETECTORS — redact-ai (v0.1)

> Status: Draft. Concrete implementation specifications for every
> baseline rule listed in [`REDACTION_RULES_v0.1.md`](./REDACTION_RULES_v0.1.md).
> Companion to [`BUILD_SPEC_v0.1.md`](./BUILD_SPEC_v0.1.md).

Each detector is implemented as a class in
`src/redact_ai/pipeline/detect/`. All detectors implement:

```python
class Detector(Protocol):
    rule_id: ClassVar[str]
    category: ClassVar[Category]

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        ...
```

A detector's output is a list of `Finding` records, each with a
`bbox` covering the matched tokens (computed via `union_bboxes`) and
a `confidence` in `{LOW, MEDIUM, HIGH}` chosen per rule below.
Locale: **`en-US` only in v0.1**.

---

## Conventions

- Regexes are written in Python `re` syntax with `re.IGNORECASE`
  unless noted. Anchors use `\b` word-boundaries except where the
  surrounding glyphs are part of the entity (e.g. `+` in phone
  numbers).
- "Token-aware" means: regex is applied to the *line text* (tokens
  joined by single spaces), then matched character ranges are mapped
  back to the covered tokens by character offset.
- "Layout-aware" means: the rule consults adjacent tokens, line
  positions, or block types in addition to text.
- Every detector returns at least `MEDIUM` confidence on a regex
  match; confidence is upgraded to `HIGH` by checksum or strong
  context, and downgraded to `LOW` only by OCR token confidence
  (see `BUILD_SPEC_v0.1.md` §12).

---

## IDENTITY

### ID-001 — Full personal names

- **Approach:** Dictionary + heuristic. Ship a bundled list of
  ~5,000 common given names (`names_given_en_us.txt`) and ~5,000
  surnames (`names_family_en_us.txt`) sourced from US census public
  data.
- **Match rule:** Two consecutive title-case tokens where the first
  is in `given` and the second is in `family`, OR three tokens where
  the middle is a single capital letter / single capital + period.
- **Negative filter:** Skip if either token is in `stopwords_caps`
  (e.g. `"New"`, `"York"`, `"Monday"`, month names, weekday names).
- **Confidence:**
  - `HIGH` if both tokens are dictionary hits AND token confidence
    ≥ 0.85.
  - `MEDIUM` otherwise (at least one dictionary hit).
- **Bbox:** Union of matched-token bboxes.

### ID-002 — Date of birth

- **Approach:** Regex over line text, with contextual "DOB"
  proximity boost.
- **Regex:**
  ```
  \b(?:0?[1-9]|[12]\d|3[01])[\/\-.\s](?:0?[1-9]|1[0-2])[\/\-.\s](?:19|20)\d{2}\b
  | \b(?:19|20)\d{2}[\/\-.\s](?:0?[1-9]|1[0-2])[\/\-.\s](?:0?[1-9]|[12]\d|3[01])\b
  ```
- **Validation:** Parse with `datetime.strptime`; reject if invalid
  date (Feb 30 etc.).
- **Confidence boost:** `HIGH` if `DOB`, `Date of Birth`, `D.O.B.`,
  `Born` appears within 32 px to the left or above the match (same
  block). Otherwise `MEDIUM`.

### ID-003 — Government ID numbers (generic)

- **Approach:** Layout-aware label trigger.
- **Trigger labels (case-insensitive):** `SSN`, `Social Security`,
  `National ID`, `NIN`, `Aadhaar`, `PAN`, `Tax ID`, `TIN`, `EIN`.
- **Match rule:** Within the same block and within 64 px to the
  right or below the trigger, match the first run of
  `[\d\s\-]{6,20}` containing ≥ 6 digits.
- **Confidence:** `HIGH` (label-anchored).
- **Notes:** Specific national IDs with their own checksums (Aadhaar
  Verhoeff, US SSN area-group rules) are NOT validated in v0.1; the
  label-anchor is treated as sufficient evidence.

### ID-004 — Passport numbers

- **Approach:** Label-triggered + format regex (US-centric).
- **Trigger labels:** `Passport`, `Passport No`, `Passport Number`.
- **Regex (within 64 px of trigger):** `\b[A-Z][0-9]{8}\b` (US
  format) OR `\b[A-Z]{2}[0-9]{7}\b` (UK/IN/etc. fallback).
- **Confidence:** `HIGH`.

### ID-005 — Driver's licence numbers

- **Approach:** Label-triggered.
- **Trigger labels:** `DL`, `Driver`, `License`, `Licence`,
  `DLN`.
- **Regex (within 64 px of trigger):** `\b[A-Z0-9]{6,14}\b` with at
  least one digit and one letter.
- **Confidence:** `MEDIUM` (no national checksum in v0.1).

---

## CONTACT

### CO-001 — Email addresses

- **Regex (token-aware):**
  ```
  \b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}\b
  ```
- **Confidence:** `HIGH`.

### CO-002 — Phone numbers

- **Regex:**
  ```
  (?<![\d/])(?:\+?\d{1,3}[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}(?!\d)
  ```
- **Validation:** Strip non-digits; require 10–15 digits.
- **Negative filter:** Skip if surrounding text matches `version`,
  `v\.?\d`, `port`, `pid` (avoids "v1.2.3.4" and similar).
- **Confidence:**
  - `HIGH` if leading `+` country code present.
  - `MEDIUM` otherwise.

### CO-003 — Postal addresses (multi-line)

- **Approach:** Layout + dictionary. A postal address is a
  *contiguous run of lines* where:
  1. One line matches the street-line regex
     `^\d{1,5}[A-Za-z]?\s+[A-Z][\w'.\-]+(\s+[A-Z][\w'.\-]+){0,3}\s+(St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Ln|Lane|Dr|Drive|Way|Ct|Court|Pl|Place|Sq|Square)\b`,
     **or** is preceded by a label `Address`, `Addr`, `Mailing`.
  2. The next line matches a city/state/ZIP pattern
     `^[A-Z][\w'.\- ]+,?\s+[A-Z]{2}\s+\d{5}(?:-\d{4})?\b`,
     **or** the next line matches an ISO country name in
     `countries_en.txt`.
- **Bbox:** Union over both lines (and any intervening lines within
  the same block).
- **Confidence:** `HIGH` if both lines match; `MEDIUM` if only the
  street-line regex matches and the line directly above contains
  a known label.

---

## FINANCIAL

### FI-001 — Card numbers (PAN)

- **Regex:** `(?<!\d)(?:\d[ \-]?){13,19}(?!\d)`
- **Validation (Luhn):**
  ```python
  def luhn_ok(s: str) -> bool:
      d = [int(c) for c in s if c.isdigit()]
      if not 13 <= len(d) <= 19: return False
      checksum = 0
      for i, n in enumerate(reversed(d)):
          if i % 2 == 1:
              n *= 2
              if n > 9: n -= 9
          checksum += n
      return checksum % 10 == 0
  ```
- **Confidence:** `HIGH` if Luhn passes; otherwise the match is
  discarded.

### FI-002 — IBAN

- **Regex:** `\b([A-Z]{2})\d{2}(?:[ ]?[A-Z0-9]){11,30}\b`
- **Validation (mod-97):**
  ```python
  def iban_ok(raw: str) -> bool:
      s = re.sub(r"\s+", "", raw).upper()
      if not 15 <= len(s) <= 34: return False
      rearranged = s[4:] + s[:4]
      digits = "".join(str(ord(c) - 55) if c.isalpha() else c
                       for c in rearranged)
      return int(digits) % 97 == 1
  ```
- **Confidence:** `HIGH` if mod-97 passes; otherwise discard.

### FI-003 — Generic bank account numbers

- **Approach:** Label-triggered.
- **Trigger labels:** `Account`, `A/C`, `Acct`, `Acct No`.
- **Match rule (within 96 px of trigger, same block):** Match the
  first `[\d\s\-]{6,20}` with ≥ 6 digits.
- **Negative filter:** Skip if the digit run also Luhn-validates
  (then it is FI-001) or mod-97 validates (then it is FI-002).
- **Confidence:** `MEDIUM`.

### FI-004 — CVV / expiry adjacent to a PAN

- **Approach:** Conditional. Only fires if FI-001 already matched
  in the same block.
- **Match rule:** Within 200 px of an FI-001 finding, match either:
  - `\b(0[1-9]|1[0-2])[\/\-](\d{2}|\d{4})\b` (expiry)
  - `\b\d{3,4}\b` (CVV) where the surrounding line contains the
    word `CVV`, `CVC`, or `Sec(?:urity)? Code`.
- **Confidence:** `HIGH` (PAN-anchored).

---

## HEALTH

### HE-001 — Medical record numbers

- **Approach:** Label-triggered.
- **Trigger labels:** `MRN`, `Medical Record`, `Patient ID`,
  `Chart No`.
- **Regex (within 96 px):** `\b[A-Z0-9\-]{4,16}\b` containing ≥ 3
  digits.
- **Confidence:** `HIGH`.

### HE-002 — Common diagnosis codes (ICD-10)

- **Default: OFF** (per `REDACTION_RULES_v0.1.md`).
- **Regex:** `\b[A-TV-Z][0-9]{2}(?:\.[0-9A-TV-Z]{1,4})?\b`
- **Confidence:** `MEDIUM`.

### HE-003 — Prescription details

- **Default: OFF.**
- **Trigger labels:** `Rx`, `Prescription`, `Sig`.
- **Match rule (within 200 px, same block):** From the trigger to
  end of line.
- **Confidence:** `MEDIUM`.

---

## CREDENTIALS

### CR-001 — Generic high-entropy tokens

- **Regex (candidate):** `\b[A-Za-z0-9_\-]{20,}\b`
- **Validation (Shannon entropy ≥ 3.5 bits/char):**
  ```python
  from math import log2
  def shannon_bits_per_char(s: str) -> float:
      counts = Counter(s)
      n = len(s)
      return -sum((c/n) * log2(c/n) for c in counts.values())
  ```
- **Negative filter:** Skip dictionary words, hex hashes shorter
  than 32, version strings.
- **Confidence:** `HIGH` if entropy ≥ 4.0 OR the line contains the
  word `token`, `secret`, `key`, `bearer`, `authorization`;
  `MEDIUM` otherwise.

### CR-002 — SSH private keys (block markers)

- **Regex:** `-----BEGIN (?:OPENSSH|RSA|DSA|EC|PGP) PRIVATE KEY-----`
- **Behaviour:** When the marker is found, redact the entire block
  from the marker line through the matching `-----END ...-----`
  line (or to end of page if no end marker).
- **Confidence:** `HIGH`.

### CR-003 — Common cloud key prefixes

- **Regex (alternation):**
  ```
  \bAKIA[0-9A-Z]{16}\b        # AWS access key id
  | \bASIA[0-9A-Z]{16}\b      # AWS temp access key id
  | \bAIza[0-9A-Za-z\-_]{35}\b # Google API key
  | \bsk-[A-Za-z0-9]{20,}\b   # OpenAI-style
  | \bsk_live_[A-Za-z0-9]{16,}\b # Stripe live key
  | \bghp_[A-Za-z0-9]{36}\b   # GitHub PAT
  ```
- **Confidence:** `HIGH`.

---

## LOCATION

### LO-001 — GPS coordinates

- **Regex (decimal degrees):**
  ```
  (?<![\d.])-?(?:[1-8]?\d(?:\.\d+)?|90(?:\.0+)?)\s*°?\s*[NS]?
  \s*[, ]\s*
  -?(?:1[0-7]\d(?:\.\d+)?|180(?:\.0+)?|\d{1,2}(?:\.\d+)?)\s*°?\s*[EW]?(?![\d.])
  ```
- **Validation:** Latitude in `[-90, 90]`, longitude in
  `[-180, 180]`.
- **Confidence:** `HIGH`.

### LO-002 — Vehicle registration plates

- **Default: OFF in v0.1** (image-based detection deferred).
- Skipped: not implemented in v0.1.

---

## CUSTOM

### CU-001 — User-defined regex / dictionary detector

- Loaded from policy `overrides`:
  ```yaml
  detectors:
    - id: CU-001
      enabled: true
      threshold: medium
      overrides:
        kind: regex            # "regex" | "dictionary"
        pattern: "INTERNAL-[0-9]{6}"
        category: CUSTOM
        confidence: medium
  ```
- The loader compiles the pattern at policy-load time; invalid
  regex → `E_POLICY`.

---

## Detector Registry

`pipeline/detect/registry.py` exposes:

```python
REGISTRY: dict[str, type[Detector]] = {
    "ID-001": FullNameDetector,
    "ID-002": DateOfBirthDetector,
    "ID-003": GovernmentIdDetector,
    "ID-004": PassportDetector,
    "ID-005": DriverLicenceDetector,
    "CO-001": EmailDetector,
    "CO-002": PhoneDetector,
    "CO-003": PostalAddressDetector,
    "FI-001": PanDetector,
    "FI-002": IbanDetector,
    "FI-003": BankAccountDetector,
    "FI-004": CvvExpiryDetector,
    "HE-001": MrnDetector,
    "HE-002": Icd10Detector,
    "HE-003": PrescriptionDetector,
    "CR-001": HighEntropyTokenDetector,
    "CR-002": SshPrivateKeyDetector,
    "CR-003": CloudKeyDetector,
    "LO-001": GpsCoordsDetector,
    "CU-001": CustomRegexDetector,
}
```

`LO-002` is intentionally absent from the v0.1 registry.

---

## Test obligations

Every detector in this document MUST have:

1. A unit test asserting **at least one true positive** from a
   synthetic line with the bbox round-trip preserved.
2. A unit test asserting **at least one true negative** that looks
   superficially similar (e.g. `1234567890123456` that fails Luhn
   for FI-001).
3. Inclusion in at least one of `TC-001`–`TC-010` (golden test).

The test files live at `tests/unit/detect/test_<rule_id_lower>.py`.
