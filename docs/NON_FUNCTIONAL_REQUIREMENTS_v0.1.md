# NON-FUNCTIONAL REQUIREMENTS — redact-ai (v0.1)

> Status: Draft. Quality attributes the system must satisfy. Targets are
> initial estimates and will be refined alongside benchmarks.

---

## NFR-1. Performance

| ID | Requirement | Target |
| --- | --- | --- |
| NFR-1.1 | End-to-end latency for a 1080p screenshot (includes localhost HTTP roundtrip from the v0.1 web UI) | ≤ 3 seconds on a modern laptop |
| NFR-1.2 | Memory ceiling for a typical run | ≤ 1 GB peak |
| NFR-1.3 | Cold-start time | ≤ 2 seconds |

> TODO: Lock down "modern laptop" baseline (e.g. 8-core CPU, 16 GB RAM).

---

## NFR-2. Accuracy

| ID | Requirement | Target |
| --- | --- | --- |
| NFR-2.1 | Recall on baseline PII categories | ≥ 95% on the curated corpus |
| NFR-2.2 | Precision on benign screenshots | ≥ 95% (FP rate ≤ 5%) |
| NFR-2.3 | Reproducibility of identical inputs | 100% deterministic |

---

## NFR-3. Privacy

| ID | Requirement |
| --- | --- |
| NFR-3.1 | The default pipeline **MUST** run entirely on-device. The localhost loopback interface (`127.0.0.1`) used by the v0.1 web UI is considered on-device. |
| NFR-3.2 | The system **MUST NOT** transmit user content to any network endpoint without explicit, per-invocation user consent. |
| NFR-3.3 | The system **MUST NOT** persist user content beyond the lifetime of a single redaction operation, except for explicitly chosen output paths. |

See [`SECURITY_v0.1.md`](./SECURITY_v0.1.md) for threat model details.

---

## NFR-4. Reliability

| ID | Requirement |
| --- | --- |
| NFR-4.1 | The system **MUST** fail closed: no output rather than partial output. |
| NFR-4.2 | The system **MUST** be free of unhandled exceptions on the curated corpus. |
| NFR-4.3 | Crashes **MUST NOT** leave partial files in the user's filesystem. |

---

## NFR-5. Usability

| ID | Requirement |
| --- | --- |
| NFR-5.1 | A first-time user should produce a successful redaction in ≤ 2 minutes. |
| NFR-5.2 | Error messages **MUST** explain *what* failed and *what to try*. |
| NFR-5.3 | Default policies **SHOULD** be sensible without configuration. |

---

## NFR-6. Maintainability

| ID | Requirement |
| --- | --- |
| NFR-6.1 | Each pipeline component **MUST** have a documented public contract. |
| NFR-6.2 | The codebase **MUST** be modular along the lines defined in [`ARCHITECTURE_v0.1.md`](./ARCHITECTURE_v0.1.md). |
| NFR-6.3 | A new detector **SHOULD** be addable without modifying core pipeline code. |

---

## NFR-7. Portability

| ID | Requirement |
| --- | --- |
| NFR-7.1 | The system **SHOULD** target macOS, Linux, and Windows. |
| NFR-7.2 | The system **SHOULD NOT** depend on platform-exclusive APIs in the core. |
| NFR-7.3 | The v0.1 surface **MUST** run as a local web UI bound to `127.0.0.1` on all supported platforms. |

---

## NFR-8. Observability

| ID | Requirement |
| --- | --- |
| NFR-8.1 | The system **MUST** expose structured logs for failure diagnosis. |
| NFR-8.2 | Logs **MUST NOT** include raw user content or matched values. |

---

## NFR-9. Accessibility

| ID | Requirement |
| --- | --- |
| NFR-9.1 | Any user-facing surface **SHOULD** meet WCAG 2.1 AA where applicable. |

> TODO: Define accessibility checklist for the chosen UI surface.
