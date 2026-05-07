# redact-ai

**Redact before you prompt.**

`redact-ai` is a privacy-first tool that detects and redacts sensitive personal
information from **screenshots, images, and documents** before they are shared
with AI systems like ChatGPT, Claude, Gemini, or any other LLM.

> Status: **Documentation phase (v0.1).** No implementation code yet — this
> repository establishes product direction, architecture, and contributor
> guidelines first.

---

## The Problem

People routinely paste or upload sensitive material into AI chat interfaces:

- Medical reports and lab results
- Bank statements, invoices, and tax forms
- Government IDs, passports, driver's licences
- Screenshots of email threads and private chats
- Internal company documents

This creates real risks:

- **Data leakage** to third-party model providers
- **Accidental exposure** of personal data belonging to others
- **Compliance issues** (HIPAA, GDPR, SOC 2, internal policy)

There is currently no simple, image-first tool that sanitises this content
*before* it reaches an AI system.

---

## The Solution

`redact-ai` is a **privacy preprocessing layer** that sits between the user
and any AI tool:

```text
Screenshot / Image / PDF
        ↓
   OCR + Layout Analysis
        ↓
   Sensitive-Data Detection
        ↓
   Redaction (visual + textual)
        ↓
Safe Output → AI Tool
```

The output is a *new* image or document with sensitive regions visually
masked, so the user can confidently drop it into any LLM chat.

---

## Documentation

All product, architecture, and contribution material lives under [`docs/`](./docs):

| Document | Purpose |
| --- | --- |
| [PRODUCT_v0.1.md](./docs/PRODUCT_v0.1.md) | Vision, users, MVP scope |
| [IDEA.md](./docs/IDEA.md) | Origin story and motivation |
| [ARCHITECTURE_v0.1.md](./docs/ARCHITECTURE_v0.1.md) | High-level system design |
| [FUNCTIONAL_REQUIREMENTS_v0.1.md](./docs/FUNCTIONAL_REQUIREMENTS_v0.1.md) | What the system must do |
| [NON_FUNCTIONAL_REQUIREMENTS_v0.1.md](./docs/NON_FUNCTIONAL_REQUIREMENTS_v0.1.md) | Quality attributes |
| [REDACTION_RULES_v0.1.md](./docs/REDACTION_RULES_v0.1.md) | What counts as sensitive |
| [OCR_PIPELINE_v0.1.md](./docs/OCR_PIPELINE_v0.1.md) | Image → text pipeline design |
| [DATA_FLOW_v0.1.md](./docs/DATA_FLOW_v0.1.md) | How data moves through the system |
| [API_SPEC_v0.1.md](./docs/API_SPEC_v0.1.md) | Public interface contract |
| [SECURITY_v0.1.md](./docs/SECURITY_v0.1.md) | Privacy guarantees and threat model |
| [TEST_CASES_v0.1.md](./docs/TEST_CASES_v0.1.md) | Realistic example inputs/outputs |
| [UX_FLOW_v0.1.md](./docs/UX_FLOW_v0.1.md) | Step-by-step user interactions |
| [ROADMAP.md](./docs/ROADMAP.md) | Milestones and release plan |
| [CONTRIBUTING.md](./docs/CONTRIBUTING.md) | How to contribute |
| [DECISIONS.md](./docs/DECISIONS.md) | Architecture Decision Log |

---

## Repository Layout

```text
redact-ai/
├── README.md
├── LICENSE
├── .gitignore
│
├── docs/         # Product, architecture, and process documentation
├── examples/     # Sample inputs, expected outputs, illustrative screenshots
└── assets/       # Diagrams, mockups, and brand assets
```

---

## Project Principles

1. **Privacy first.** Default to local processing. Never log raw input.
2. **Image-first.** Screenshots and photos are the primary input modality.
3. **Technology-agnostic core.** Rules and contracts are defined independently
   of any specific OCR engine, ML model, or runtime.
4. **Modular.** Detection, redaction, and rendering are independently
   replaceable components.
5. **AI-friendly codebase.** Documentation is structured so AI coding agents
   can implement features without ambiguity.

---

## Status & Roadmap

This is **v0.1 — documentation only**. See
[`docs/ROADMAP.md`](./docs/ROADMAP.md) for upcoming milestones.

---

## Contributing

We welcome contributors of all kinds — engineers, designers, security
researchers, and writers. Please read
[`docs/CONTRIBUTING.md`](./docs/CONTRIBUTING.md) before opening an issue or
pull request.

---

## License

`redact-ai` is released under the [MIT License](./LICENSE).
