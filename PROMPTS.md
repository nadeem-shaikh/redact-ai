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

---

## Prompt 2 — Tech stack options analysis

You are a senior software architect and AI product engineer.
I am building an open-source project called `redact-ai`.
---
## Product Summary
redact-ai is a privacy-first tool that detects and redacts sensitive personal information (PII) from screenshots, images, PDFs, and text before users send them to AI tools like ChatGPT or Claude.
Core capabilities:
- OCR for images/screenshots
- PII detection (names, phone numbers, emails, IDs, financial/medical data)
- Redaction engine (blur/block/overlay)
- Safe output generation
- Future: browser extension + API + SaaS
---
## Your Task
Design and compare the MOST suitable tech stack options for building this system.
You MUST:
### 1. Provide 2–4 viable tech stack options
Each option should represent a different architectural approach, such as:
- Local-first CLI tool
- Python AI/ML-centric pipeline
- Hybrid API + frontend architecture
- Scalable SaaS-ready system
---
### 2. For EACH stack option include:
#### A. Stack Description
- Programming languages
- Core frameworks/libraries
- OCR approach/tools
- PII detection approach
- Image processing tools
- CLI/API/UI structure
#### B. Pros
- Strengths of the stack
- Performance advantages
- Developer experience
- Scalability potential
- Ecosystem maturity
#### C. Cons
- Weaknesses
- Complexity
- Maintenance overhead
- Deployment difficulty
- Tradeoffs
#### D. Best Fit
- When to choose this stack
- What stage of product it fits (MVP / scale / enterprise)
---
### 3. Final Recommendation Section
Provide:
- Recommended stack for MVP (v0.1)
- Recommended stack for scaling (v1.0+)
- Clear reasoning for both choices
---
## OUTPUT REQUIREMENT (IMPORTANT)
Instead of plain text output, you must generate a **Markdown file content** that is ready to be saved inside the repository.
### File details:
- File path: `/docs/TECH_STACK_OPTIONS_v0.1.md`
- Format: clean Markdown
- Must include:
  - Title
  - Sections as described above
  - Tables where useful
  - Clear headings
  - Professional documentation style
---
## Constraints
- Do NOT assume final business model
- Keep focus on MVP feasibility
- Prioritize OCR + image redaction use case
- Avoid over-engineered enterprise-only solutions
- Assume privacy-first, local-first preference is important
---
## Goal
Help select a tech stack that:
1. Enables fast MVP development
2. Supports accurate OCR + PII detection
3. Is modular and scalable
4. Can evolve into a production-ready system
---
## Output Format
Return ONLY the full Markdown file content for:
`/docs/TECH_STACK_OPTIONS_v0.1.md`
