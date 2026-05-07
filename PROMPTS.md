# Prompts

This file records the verbatim prompts used to scaffold and evolve this
repository with an AI coding agent. Keeping the prompts alongside the
code makes the project's documentation-first development process
reproducible and auditable.

---

## Prompt 1 — Initial repository scaffold

Create a clean, documentation-first repository structure for an open-source project named `redact-ai`.

Project Summary:
redact-ai is a privacy-first tool that detects and redacts sensitive personal information from screenshots, images, and documents before they are shared with AI systems like ChatGPT or Claude.

The repository should be focused on:
- product clarity
- architecture planning
- AI-assisted development
- maintainability
- extensibility

Do NOT assume any programming language or framework yet.

The goal is to establish a strong documentation foundation before implementation begins.

Generate the following repository structure exactly:

redact-ai/
├── README.md
├── LICENSE
├── .gitignore
│
├── docs/
│   ├── PRODUCT_v0.1.md
│   ├── IDEA.md
│   ├── ARCHITECTURE_v0.1.md
│   ├── FUNCTIONAL_REQUIREMENTS_v0.1.md
│   ├── NON_FUNCTIONAL_REQUIREMENTS_v0.1.md
│   ├── REDACTION_RULES_v0.1.md
│   ├── OCR_PIPELINE_v0.1.md
│   ├── DATA_FLOW_v0.1.md
│   ├── API_SPEC_v0.1.md
│   ├── SECURITY_v0.1.md
│   ├── TEST_CASES_v0.1.md
│   ├── UX_FLOW_v0.1.md
│   ├── ROADMAP.md
│   ├── CONTRIBUTING.md
│   └── DECISIONS.md
│
├── examples/
│   ├── sample_inputs/
│   ├── expected_outputs/
│   └── screenshots/
│
└── assets/
    ├── diagrams/
    ├── mockups/
    └── logos/

Requirements:
- Create placeholder content for every markdown file
- Include meaningful section headings in each document
- Keep the architecture technology-agnostic
- Focus on image-first redaction workflows
- Structure documentation for AI coding agents and open-source contributors
- Keep naming conventions clean and scalable
- Do not generate implementation code yet
- Emphasize modularity and maintainability
- Use concise but professional markdown formatting
- Include TODO placeholders where details are pending

Additional Guidance:
- PRODUCT_v0.1.md should define the product vision, users, MVP scope, and roadmap
- ARCHITECTURE_v0.1.md should define high-level system components and data movement
- FUNCTIONAL_REQUIREMENTS_v0.1.md should define exact expected behaviors
- REDACTION_RULES_v0.1.md should define what counts as sensitive information
- TEST_CASES_v0.1.md should contain realistic example inputs and expected outputs
- DECISIONS.md should be formatted as an architecture decision log
- UX_FLOW_v0.1.md should describe user interaction flows step-by-step
- SECURITY_v0.1.md should define privacy guarantees and threat considerations

The final output should look like a professional open-source project scaffold prepared for future development.
