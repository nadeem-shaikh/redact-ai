# IDEA — redact-ai

> Status: Living document. The "why" behind the project.

---

## 1. The Spark

Every day, millions of people paste screenshots into ChatGPT, Claude, and
similar tools. They're asking simple questions:

- *"Summarise this lab report."*
- *"What does this bank statement mean?"*
- *"Translate this letter."*

Almost none of them mean to share names, account numbers, addresses, or
medical IDs — but those details are right there in the image.

There is no quick, trustworthy way to *clean* a screenshot before
prompting. `redact-ai` exists to fill that gap.

---

## 2. Why Image-First

Most existing PII tools focus on plain text:

- They assume structured input.
- They lose layout when applied to documents.
- They cannot help when the user is in a hurry and just drags an image
  into a chat window.

The most natural unit of "stuff you might paste into an AI" is a
**screenshot**. By treating images as first-class input, we meet users
exactly where they already are.

---

## 3. Core Beliefs

1. **Privacy must be the default**, not a setting buried in a menu.
2. **Local processing wins trust.** A privacy tool that calls home
   contradicts itself.
3. **Redaction is a UX problem first**, an ML problem second. If it isn't
   fast and obvious, no one will use it.
4. **Open-source is non-negotiable.** Users must be able to verify what
   the tool does to their data.

---

## 4. Inspirations

- Scribbling on a whiteboard photo with a marker before sending it.
- "Markup" tools on iOS / macOS for simple image annotation.
- Differential-privacy and on-device ML in modern operating systems.
- The DevOps idea of "shifting left" — apply controls earlier in the flow.

---

## 5. Anti-Goals

- We are **not** building a general OCR product.
- We are **not** building a DLP (Data Loss Prevention) platform.
- We are **not** building a monitoring or scanning service.
- We are **not** asking users to change AI tools.

---

## 6. Naming

`redact-ai` reads as both a verb ("redact, AI") and a tagline
("redact for AI"). It hints at the workflow without describing the
implementation.

---

## 7. Future Directions (Speculative)

- Encrypted local memory of "approved" redaction policies.
- Audit trail mode for regulated industries.
- Plug-in detectors maintained by domain experts.
- Native integration with OS-level "share" sheets.

> TODO: Capture community feedback once the project is announced.
