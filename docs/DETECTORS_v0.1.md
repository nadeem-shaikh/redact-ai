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
  ```text
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

### ID-006 — Personal names via statistical NER

- **Approach:** Statistical NER. Complements ID-001 by catching
  names that are absent from the bundled US-centric given/family
  dictionaries (non-Western names, novel spellings, hyphenated
  surnames). Runs entirely on-device — no network calls (ADR-002,
  ADR-011).
- **Engine:** spaCy with `en_core_web_md` by default. The medium
  model recognises names without sentential context (e.g. a bare
  "Nadeem Shaikh" on its own line, which is the dominant input shape
  for screenshots) whereas `en_core_web_sm` requires surrounding
  punctuation. The model is overridable via the policy
  `overrides.model` field (e.g. `en_core_web_sm` for slimmer installs,
  `en_core_web_lg`/`_trf` for higher recall, or a multilingual model).
- **Match rule:** For every OCR line, run the spaCy pipeline (NER
  components only — `lemmatizer`, `tagger`, and `attribute_ruler`
  are disabled to keep cold-start under NFR-1.3) and emit a finding
  for every entity whose label is `PERSON`. Character offsets are
  mapped back to OCR tokens via the same `tokens_covering` helper
  used by regex-based detectors.
- **Confidence:**
  - `HIGH` if the matched entity spans two or more OCR tokens (a
    full first-last pair is much less likely to be a spurious
    capitalised noun).
  - `MEDIUM` for single-token PERSON entities.
  - OCR-derived confidence floor still applies via
    `cap_confidence`.
- **Bbox:** Union of matched-token bboxes.
- **Determinism:** spaCy NER with greedy decoding is deterministic
  for a fixed model version and input (NFR-2.3). The runtime pins
  `spacy==3.7.5`; the `en_core_web_md` version installed by the
  user is recorded in the manifest header for reproducibility.
- **Install:** Both `spacy` and the `en_core_web_md` model wheel are
  declared as required dependencies of `redact-ai`. `pip install`,
  `uv sync`, and `pipx install` pull both automatically (ADR-011).
  If the model is missing at runtime (manual environment surgery),
  the detector raises `E_POLICY` with a clear hint, consistent with
  ADR-005 fail-closed semantics.
- **Trade-off:** ID-001 (dictionary) and ID-006 (NER) can both fire
  on the same span. The merge stage already de-duplicates
  overlapping findings within a category, so the user sees one
  redaction per span; the manifest records both rule IDs for audit.
- **Variant scanning:** after the NER pass, ID-006 derives slug-style
  variants of every detected `PERSON` and re-scans the document for
  them. Generated forms include:
  - Combined slug forms (`nadeem-shaikh`, `nadeem_shaikh`,
    `nadeem.shaikh`, `nadeemshaikh`).
  - First-initial-plus-last forms (`nshaikh`, `n-shaikh`,
    `n.shaikh`).
  - Standalone first and last names alone (`nadeem`, `shaikh`) so
    that handles like `nadeem/redact-ai` or `shaikh/redact-ai` are
    caught.

  This catches GitHub-style usernames, email locals, and similar
  handles that share the same identity but aren't recognised by NER
  themselves. Variants shorter than 5 characters are excluded to
  avoid generic matches; variant findings are emitted at `medium`
  confidence.

### ID-008 — Payment-recipient names (label-triggered)

- **Approach:** Layout-aware label trigger. Catches recipient names on
  payment-receipt screenshots where the name is rendered all-caps
  and/or is non-Western — two cases where ID-001 (US dictionary) and
  ID-006 (statistical NER on a cased model) both reliably miss.
- **Trigger labels (case-insensitive):** `Paid to`, `Pay to`,
  `Payee`, `Beneficiary`, `Recipient`, `Receiver`, `Sender`,
  `Sent to`, `Transferred to`, `Account Holder`, `Account Name`.
- **Match rule:** Within the same block, on the trigger line (to the
  right of the label) or within 96 px below, capture a contiguous run
  of 2–5 capitalised tokens matching `^[A-Z][A-Za-z'\-]+$`. Stopword
  tokens (`stopwords_caps_en.txt`) break the run.
- **Confidence:** `HIGH` (label-anchored).

### ID-007 — Face photo detector (vision)

- **Approach:** OpenCV Haar cascade (`haarcascade_frontalface_default.xml`)
  applied to the ingested `original` image. Profile photos, avatars,
  and similar headshots that leak identity are redacted alongside
  text-based PII (ADR-012). This is a *vision* detector and consumes
  the raw image, not OCR output, so it lives under
  `pipeline/detect/vision/` and is dispatched via a separate
  `VISION_REGISTRY`.
- **Engine:** `opencv-python-headless`'s bundled
  `haarcascade_frontalface_default.xml`. No additional model download.
- **Match rule:** Run `detectMultiScale` with
  `scaleFactor=1.1`, `minNeighbors=5`, and a minimum face size of
  4 % of the short image side. All three knobs are overridable via
  policy `overrides.scale_factor`, `min_neighbors`, and
  `min_size_fraction` for users who need to bias toward recall or
  precision.
- **Confidence:** `MEDIUM` (Haar gives no per-detection score; the
  `min_neighbors` gate is the implicit confidence filter).
- **Bbox:** Returned in original input pixel coordinates so the
  redactor masks the same region the user uploaded.
- **Determinism:** Haar cascades are pure C++ with no stochastic
  components — bit-deterministic for a fixed input (NFR-2.3).
- **Limitations:** Frontal faces only. Profile-view, heavily
  occluded, or very small faces are missed. The trigger to swap
  this for a heavier detector (MediaPipe / YOLO-face) is corpus
  face-recall < 90 %.

---

## CONTACT

### CO-001 — Email addresses

- **Regex (token-aware):**
  ```text
  \b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}\b
  ```
- **Confidence:** `HIGH`.

### CO-002 — Phone numbers

- **Regex:**
  ```text
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

### FI-005 — Masked account / card numbers

- **Approach:** Standalone regex. A run of mask glyphs adjacent to a
  short digit suffix is an unambiguous reference to a sensitive
  identifier — no label trigger is required because the mask glyphs
  themselves are the signal. Catches the dominant mobile-payment UI
  pattern (e.g. `******1234`, `XXXX5678`, `••••9012`).
- **Mask glyphs:** `*`, `X` (uppercase only — lowercase `x` is too
  ambiguous with technical contexts like `x86`), `•`, `·`, `●`.
- **Match rule:** ≥ 2 mask glyphs immediately followed by ≥ 2 digits
  (suffix form), or a `digits-mask-digits` sandwich form. Tokens
  with separators (`\s`, `-`) between glyphs are tolerated.
- **Confidence:** `HIGH` (mask-glyph signature is the validator).

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
  ```text
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
  ```text
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

## ML ENGINE

### ML-001 — GLiNER strong PII engine (optional)

- **Approach:** Statistical, transformer-based generalist NER. A single
  model scores a configurable label schema over each OCR line in one
  deterministic forward pass, catching PII across every category that
  the regex/dictionary/label rules miss (non-Western names, unlabeled
  IDs, addresses without a street suffix, PHI in prose). Complements —
  does not replace — the deterministic detectors, which stay
  authoritative for structured identifiers (Luhn PANs, IBAN mod-97,
  cloud-key prefixes). See ADR-013.
- **Engine:** [GLiNER](https://github.com/urchade/GLiNER) via the
  `gliner` package. Default model `urchade/gliner_multi_pii-v1`; the
  SOTA `GLiNER2-PII` checkpoint or `nvidia/gliner-PII` are reachable via
  the policy `overrides.model` field.
- **Packaging:** Optional. Ships in the `redact-ai[strong]` extra and is
  `enabled: false` in the default policy. Enable it (and install the
  extra) via `examples/strong_policy.yaml`. Registering the detector
  does not pull torch — `gliner` is imported lazily on first use.
- **Match rule:** For every OCR line, run `predict_entities(text,
  labels, threshold)`. Each returned entity's label is mapped to a
  redact-ai `Category` via the label→category map; character offsets are
  mapped back to OCR tokens with the same `tokens_covering` helper the
  regex detectors use.
- **Category:** Per finding, from the label map (a single detector spans
  multiple categories). Default map: person / DOB / passport / driver's
  license / SSN / national-id / tax-id → `IDENTITY`; email / phone /
  address → `CONTACT`; credit-card / bank-account / IBAN → `FINANCIAL`;
  medical-record-number / health-condition → `HEALTH`; api-key /
  password / secret → `CREDENTIALS`; gps-coordinates → `LOCATION`.
- **Confidence:** From the model span score — `HIGH` ≥ 0.85, `MEDIUM` ≥
  0.65, else `LOW` — then capped by the OCR token-confidence floor via
  `cap_confidence`.
- **Overrides:** `model` (str), `revision` (str — commit/tag to pin the
  weights; a bare `model` override clears the default's pinned revision),
  `score_threshold` (float in `[0, 1]`), `labels` (`{label: category}`
  map), `allow_download` (bool, default `false`). Invalid overrides raise
  `E_POLICY`.
- **Determinism:** Model in eval mode with greedy/argmax decoding, and the
  default weights pinned to an immutable commit revision — a pure function
  of `(model revision, input)` on a fixed machine (NFR-2.3).
- **Local-first:** Loaded with `local_files_only` from the local Hugging
  Face cache; the redaction hot path never reaches the network (ADR-002).
  Pre-fetch once with `huggingface-cli download <model> --revision <rev>`,
  or set `allow_download: true` for a one-time online fetch. A cold cache
  fails closed rather than blocking on the network.
- **Fail-closed:** Enabled without the `gliner` package or a cached model →
  the detector raises `E_POLICY`, and the pipeline treats that as **fatal**
  for the whole request (not a partial-failure warning), so a run never
  silently completes missing the engine the user opted into (ADR-005).

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
    "ID-006": PersonNameNerDetector,
    # ID-007 lives in VISION_REGISTRY (vision detector); see ADR-012.
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
    "ML-001": GlinerPiiDetector,  # optional strong engine (ADR-013)
}
```

`LO-002` is intentionally absent from the v0.1 registry. `ML-001` is
registered but disabled by default and only runs when the
`redact-ai[strong]` extra is installed and the rule is enabled in policy.

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
