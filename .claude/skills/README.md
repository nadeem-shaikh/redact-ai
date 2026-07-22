# Vendored skills — Compound Engineering

This directory vendors the **Compound Engineering** skill set so the
workflow travels with the repository and is available to Claude Code
sessions started anywhere under it (project skills load from
`.claude/skills/`).

## Provenance

- **Source:** [`EveryInc/compound-engineering-plugin`](https://github.com/EveryInc/compound-engineering-plugin)
- **Plugin version:** `3.19.0`
- **Vendored commit:** `47f784ebb8cf104076a308c60115ffed702e3c6e`
- **License:** MIT © 2025 Every — see [`LICENSE`](./LICENSE)
- **Vendored:** 2026-07-21

Only the `skills/` tree from the upstream plugin is vendored (SKILL.md
files plus their `references/` and `scripts/`). The upstream `src/`,
`docs/`, and packaging files are intentionally omitted.

## What's here

The Compound Engineering loop — brainstorm → plan → work → review —
plus supporting skills. Entry points used most often:

- `ce-plan/` — turn a request or requirements doc into a durable
  implementation plan (`docs/plans/…`).
- `ce-work/` — execute an implementation-ready plan.
- `ce-brainstorm/`, `ce-code-review/`, `ce-debug/`, `ce-commit/`, … —
  the rest of the loop.

## Updating

Re-vendor from upstream rather than editing in place, so local changes
never diverge silently:

```bash
git clone --depth 1 https://github.com/EveryInc/compound-engineering-plugin.git /tmp/ce
rm -rf .claude/skills && mkdir -p .claude/skills
cp -R /tmp/ce/skills/. .claude/skills/
cp /tmp/ce/LICENSE .claude/skills/LICENSE
# then refresh the provenance block above (version + commit + date)
```
