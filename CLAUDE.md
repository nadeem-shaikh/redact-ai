# redact-ai — Claude memory

## Git workflow

When a task that produces code changes is complete:

1. **Branch.** Develop on the task's designated branch
   (`claude/<slug>`). Never push to `main` directly. If the task didn't
   specify a branch, create one before the first commit.
2. **Verify locally.** Before committing, run the project gates so
   broken work never reaches the remote:
   ```bash
   uv run --extra dev ruff check src tests
   uv run --extra dev ruff format --check src tests
   uv run --extra dev mypy --strict src
   uv run --extra dev pytest tests/unit
   ```
3. **Commit + push.** Stage only the files actually touched (no
   `git add -A` / `.` blanket adds). Use `git push -u origin <branch>`
   with up to 4 retries on network failure (2s / 4s / 8s / 16s
   backoff). Never `--force` / `--force-with-lease` without an
   explicit request from the user, except to scrub PII or secrets.
4. **Always open a pull request.** As soon as the branch is pushed
   and the task is complete, open a PR against `main` using
   `mcp__github__create_pull_request`. The PR title must be ≤ 70
   chars; the body uses the standard `## Summary` / `## Test plan`
   shape. Do this proactively — do not wait for the user to ask.
5. **Subscribe to the PR.** Immediately call
   `mcp__github__subscribe_pr_activity` for the new PR so CI failures
   and review comments wake the session. End the turn after
   subscribing — do not poll with `sleep` or repeated status checks.
6. **Address feedback.** When a `<github-webhook-activity>` event
   arrives, investigate it. Push small unambiguous fixes directly;
   ask via `AskUserQuestion` for anything architecturally significant
   or ambiguous; skip events that need no action.
7. **Unsubscribe on merge.** When the merge event arrives, treat the
   PR as closed: do not reopen or open follow-up PRs for the same
   change unless the user asks.

## PII / secrets

Never commit real names, account numbers, phone numbers, addresses,
keys, or other PII into:

- source files (tests included),
- commit messages,
- PR titles or bodies.

Use clearly synthetic placeholders (`JOHN DOE`, `ANJALI VENKATESHA
NAIDU`, `******1234`, `4111-1111-1111-1111`). If PII leaks despite
this, scrub the working tree, squash the affected commits, and
force-push (with `--force-with-lease`) — this is the one
force-push case that doesn't need explicit per-action approval.

## Tone for code & commits

- No comments unless the *why* is non-obvious.
- No "added for X" / "used by Y" comments — that belongs in the PR.
- Commit messages: subject ≤ 72 chars, body wraps at ~72, focus on
  *why* not *what*.

## Tools

- Prefer dedicated tools (Read / Edit / Write) over `cat` / `sed` /
  `echo`.
- For GitHub interactions use `mcp__github__*` only — no `gh` CLI.
- Only operate on `nadeem-shaikh/redact-ai`.
