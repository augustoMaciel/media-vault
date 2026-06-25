# Working Agreement for Claude Code (phased, approval-gated build)

This repo is built in **strict phases**. Follow them in order. Do NOT skip ahead,
and do NOT write any file until I have approved its contents.

All project specifics — stack, project description, the full file/directory
structure, the per-file build notes, the build order, and what is in/out of
scope — live in the **architecture file: `STRUCTURE.txt`**. Treat it as the
single source of truth. This file (`CLAUDE.md`) only defines the *process*.

## Global rules (every phase)

1. **Never call `Write`/`Edit` until I approve the exact content.** For each file:
   - First print the **full proposed file content** in a code block.
   - Briefly explain key decisions (1–3 bullets).
   - Then STOP and ask: "Approve, or edits?" Wait for my reply.
   - If I request changes, revise and re-print the full file, then ask again.
   - Only after I say "approve"/"go" do you write it.
2. **One file at a time.** Do not batch multiple file writes in a turn.
3. After writing a file, give a one-line summary and name the **next** file you
   propose — then wait for me to say continue.
4. Match the style, comments, and idioms already present in the repo.
5. Follow the order, responsibilities, and scope defined in `STRUCTURE.txt`.
   If anything there seems wrong or unclear, raise it BEFORE coding.

## Phase 0 — Architecture (read-only)
- Read `STRUCTURE.txt`. It begins with the **stack** and a **project
  description**, then defines every file/directory, the build order, and scope.
- Confirm understanding and surface any gaps or contradictions.
- If I ask, IMPROVE `STRUCTURE.txt` (or the scaffold comments) — but treat those
  edits like any other file: propose, wait, then write.
- Produce nothing else. End by listing the file order for Phase 1 (from STRUCTURE.txt).

## Phase 1 — Backend (data + domain + services)
- Implement the backend foundation file-by-file, in the order given in
  `STRUCTURE.txt` (models/config/factory/security/validation/storage, etc.).
- When persistence is ready, propose any DB migration/setup commands for me to run.
- Apply the global rules: show code, wait, edit, write.

## Phase 2 — API (request/response layer + tests)
- Implement the HTTP layer file-by-file per `STRUCTURE.txt`
  (schemas/validation → route handlers → tests).
- Honor the security and validation rules called out in `STRUCTURE.txt`.
- Same loop: show code, wait, edit, write.

## Phase 3 — Frontend (client app)
- Implement the frontend file-by-file per `STRUCTURE.txt`
  (types → api client → state/context → routing → pages/components).
- Same loop: show code, wait, edit, write.

## Scope
- Build only what `STRUCTURE.txt` defines as in-scope. Anything it marks
  "out of scope" / "descoped" must NOT be implemented unless I explicitly ask.
