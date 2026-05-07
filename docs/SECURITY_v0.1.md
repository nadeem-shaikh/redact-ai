# SECURITY — redact-ai (v0.1)

> Status: Draft. Privacy guarantees, threat model, and security
> commitments for `redact-ai`.

---

## 1. Privacy Promises

1. **Local by default.** The default pipeline runs entirely on the
   user's device.
2. **No telemetry of user content.** We never collect, transmit, or
   store the content the user is redacting.
3. **No silent network calls.** The default policy makes zero outbound
   network requests during a redaction operation.
4. **Fail closed.** If the system cannot guarantee a safe redaction, it
   produces no output image.
5. **Auditable.** Every redaction is traceable to a rule and a region;
   every release is reproducible.

---

## 2. Threat Model

### 2.1 Assets

| Asset | Description |
| --- | --- |
| Raw user input | The original sensitive image / document |
| OCR-extracted text | Plaintext recognised from the image |
| Findings | Detected sensitive entities (text + location) |
| Redacted output | The de-identified artefact the user shares |

### 2.2 Adversaries

| Adversary | Concern |
| --- | --- |
| Network attacker | Intercepting transmitted content |
| Local malware | Reading process memory or filesystem |
| Compromised dependency | Exfiltrating data via supply chain |
| Curious bystander | Viewing screen during redaction |
| The downstream AI tool | Receiving more than it should |

### 2.3 Trust Boundaries

- **Inside trust:** the user's process, memory, and chosen output paths.
- **Outside trust:** the network, the AI tool, third-party services.

### 2.4 Out-of-Scope (for v0.1)

- Hardened protection against an attacker with root on the device.
- Side-channel attacks (cache, timing, power).
- Tamper-resistant audit logging.

---

## 3. Risks & Mitigations

| Risk | Mitigation |
| --- | --- |
| Sensitive data leaks via logs | Logs **MUST NOT** contain raw input or matched values |
| Sensitive data persists in temp files | Pipeline operates in-memory; temp files only with explicit consent |
| Detector false negative leaks data | Strict mode + high recall by default; warn on low coverage |
| Compromised dependency exfiltrates data | Reproducible builds, dependency pinning, minimal supply chain |
| Output image still contains pixels of sensitive content | Redactor enforces opaque overlay; pixel-level test in CI |
| Manifest leaks via "verbose report" mode | Verbose mode is opt-in per invocation, never default |

---

## 4. Data Handling

| Data | Storage | Retention |
| --- | --- | --- |
| Raw input | Memory only | Lifetime of the operation |
| OCR text | Memory only | Lifetime of the operation |
| Findings | Memory only | Until manifest is built |
| Redacted output | User-chosen path | User-controlled |
| Manifest | User-chosen path | User-controlled |
| Logs | User filesystem | User-controlled |

---

## 5. Cryptography

- Hashes in the manifest **MUST** use SHA-256 or stronger.
- If signing is added, the system **MUST** use modern, audited primitives.

> TODO: Decide whether to sign manifests by default.

---

## 6. Supply Chain

- Pin all dependencies by exact version + hash.
- Reproducible builds for distributed binaries.
- Publish SBOMs alongside releases.
- Document a minimal trusted dependency list.

> TODO: Choose tooling once language is selected.

---

## 7. Responsible Disclosure

A `SECURITY.md` at the repository root will describe how to report
vulnerabilities. Until then, please open a private security advisory
through the project's hosting platform.

> TODO: Move disclosure policy into a top-level `SECURITY.md`.

---

## 8. Open Questions

- Should we sandbox OCR engines that run untrusted models? *(TODO)*
- Do we need a "sealed mode" that hides even the manifest from logs? *(TODO)*
- How do we communicate the residual risk of OCR misses to the user? *(TODO)*
