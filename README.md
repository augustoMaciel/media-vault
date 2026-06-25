# Media Vault

A private file manager. Each authenticated user can upload, browse, search,
download, version, and delete **only their own** files
(`.png .jpg .jpeg .pdf .txt`, max 10 MB). Built for the Pixel Breeders Junior
Web Dev test.

---

## Quick start

```bash
cp .env.example .env          # defaults work locally
docker compose up --build     # one command, all services
```

| Service        | URL                     |
|----------------|-------------------------|
| Frontend (SPA) | http://localhost:5173   |
| Backend API    | http://localhost:5000   |
| MinIO console  | http://localhost:9001   |

On boot the backend runs `flask db upgrade` (applying the committed migrations to
a fresh MySQL) and then serves. Register an account and start uploading.

---

## Architecture

```
                Browser — React + TypeScript SPA (:5173)
                        │  JWT bearer token
                        ▼
                Flask REST API (:5000)
         app factory · blueprints · services · core
              │                         │
     metadata │                         │ file bytes (streamed)
              ▼                         ▼
        MySQL 8 (:3306)          MinIO / S3 (:9000)
   one row per file +           objects under <owner>/<uuid>.<ext>
   one row per version          (private bucket)
```

**Two core ideas:**

1. **Metadata / object split** — MySQL stores the metadata (owner, name, MIME,
   size, date, storage key, version history); MinIO stores the bytes. File bytes
   never touch the database.
2. **Ownership enforcement** — every row is owned by a user; every `/media`
   route is JWT-authenticated and filtered by owner. Single-item routes return
   **404** (never 403) when the row isn't the caller's, so existence isn't leaked.

### Code organization (key structural decision)

The guiding principle is a **clean separation of concerns for readability: each
file represents one working part of the system.** That keeps responsibilities
isolated and the project easy to navigate — a deliberate choice for a
maintainable, junior-level codebase over cramming logic together.

```
backend/app/
  config.py          env-driven config, limits, whitelists
  extensions.py      db / migrate / jwt / cors singletons
  models/            User, Media, MediaVersion (SQLAlchemy)
  schemas/           marshmallow validation + serialization
  core/              security (hash/JWT), validators (upload safety)
  services/          storage (MinIO), thumbnails (Pillow)
  blueprints/        auth + media HTTP routes
  tests/             pytest (auth + media, incl. isolation/SQLi)

frontend/src/
  types/             shared TS models
  api/               axios client + auth/media endpoint wrappers
  context/           AuthContext (session)
  components/        Thumb, UploadForm, Search/Versions/Detail panels, ProtectedRoute
  pages/             Login, Register, Vault (3-panel layout)
```

---

## Tech stack

- **Frontend:** React + TypeScript (Vite), react-router, axios
- **Backend:** Flask (application factory + blueprints), SQLAlchemy, Flask-Migrate
- **Database:** MySQL 8 (PyMySQL)
- **Storage:** MinIO (S3-compatible)
- **Auth:** JWT (Flask-JWT-Extended, HS256), bcrypt (passlib)
- **Infra:** Docker Compose (db · minio · createbuckets · backend · frontend)

---

## API

Resources are addressed by an opaque random `id` (`public_id`), not a sequential
integer. All `/media` routes and `/auth/me` require `Authorization: Bearer <token>`.

| Method | Path | Purpose |
|--------|------|---------|
| POST   | `/auth/register` | create account (auto-login) |
| POST   | `/auth/login` | authenticate → `{access_token, user}` |
| GET    | `/auth/me` | restore session |
| GET    | `/media[?q=]` | list/search my files (current version) |
| POST   | `/media` | upload (multipart: file, title*, description) |
| GET    | `/media/{id}/download` | stream current version (attachment) |
| GET    | `/media/{id}/link` | expiring presigned URL |
| GET    | `/media/{id}/thumbnail` | current thumbnail (ETag/304) |
| GET    | `/media/{id}/versions` | version history |
| POST   | `/media/{id}/versions` | upload a new version |
| PATCH  | `/media/{id}/versions/{n}` | edit a version's description |
| GET    | `/media/{id}/versions/{n}/download` | download a specific version |
| GET    | `/media/{id}/versions/{n}/thumbnail` | a version's thumbnail |
| DELETE | `/media/{id}/versions/{n}` | delete one version (renumbers the rest) |
| DELETE | `/media/{id}` | delete a file and all its versions |
| GET    | `/health` | liveness |

`*` Title is required (server-enforced).

---

## Security

- **JWT pinned to HS256** (`JWT_DECODE_ALGORITHMS`) — blocks `alg:none` /
  algorithm-confusion forgeries. Identity is the signed token, not client input.
- **Passwords** bcrypt-hashed, never returned; strong policy (≥10 chars,
  upper/lower/digit/symbol, common-password blocklist); login is a generic 401
  with timing equalization to prevent account enumeration.
- **Upload anti-forgery** — client Content-Type and extension are never trusted;
  files are sniffed by magic bytes **and deep-validated** (images fully decode
  with Pillow + decompression-bomb guard, PDFs must carry `%PDF-`, `.txt` must be
  all UTF-8/no NUL). Bytes are stored under an opaque `<owner>/<uuid>` key, the
  bucket is private, and downloads are served as `attachment` — nothing is ever
  executed or served inline.
- **SQL-injection-proof search** — owner-scoped ORM query with `ilike` over
  **bound parameters** and **escaped LIKE wildcards** (`% _ \`); payloads like
  `' OR '1'='1` are treated as literal text (regression-tested).
- **Opaque resource IDs** — the API uses a 128-bit random `public_id`, not the
  sequential PK, so resources can't be enumerated. (Defense-in-depth: IDOR is
  already prevented by the per-request ownership 404.)
- **Consistent JSON errors** — 400/401/404/413 + a global 500 handler, so even an
  unexpected failure (e.g. storage down) returns parseable JSON, not an HTML page.

---

## Technical decisions

- **Each file = one responsibility** (see Code organization) — the primary
  structural decision, chosen for readability and maintainability.
- **Stream downloads through Flask** rather than presigned URLs by default — a
  MinIO presigned URL embeds the internal `minio:9000` host, unreachable from the
  browser (presigned links are offered as a separate bonus endpoint).
- **`filetype` over `python-magic`** — pure-Python, no `libmagic` in the image.
- **Pinned `bcrypt==4.0.1`** (passlib 1.7.4 breaks on bcrypt ≥4.1) and added
  **`cryptography`** (PyMySQL needs it for MySQL 8's `caching_sha2_password`).
- **Token in `localStorage`** for a persistent session (UX); the XSS trade-off is
  acknowledged — a hardened deployment would use httpOnly cookies + CSRF + HTTPS.
- **Versioning model** — `Media` is the current snapshot; `MediaVersion` holds
  history. Deleting a version renumbers the rest contiguously and repoints the
  snapshot if the current version was removed; deleting the last version deletes
  the file.

---

## AI usage

This project was built with **Claude Code** (Anthropic), used as a pair-programmer
under a **strict, candidate-driven, approval-gated workflow** — not
autogenerated:

1. **I authored the base structure first.** Before any code, I defined the
   architecture in `STRUCTURE.txt` — the stack, the full file/directory layout,
   per-file responsibilities, the build order, and what was in/out of scope. That
   document is the single source of truth the implementation followed.
2. **Implementation proceeded in phases, validating every file.** Work went
   phase by phase (backend foundation → API → frontend). For **each file**, the AI
   proposed the full content plus its key decisions, and **I reviewed and explicitly
   approved (or requested changes) before it was written** — one file at a time. I
   directed scope and trade-offs throughout and can explain every decision.

**Examples of changes I requested and directed:**

- **Opaque IDs (anti-enumeration / IDOR):** I asked to stop exposing the
  sequential integer PK and address resources by a random `public_id`
  (`secrets.token_urlsafe`, 128-bit). The AI flagged that the *primary* IDOR
  control was already the ownership 404; I had it add opaque IDs as
  defense-in-depth, with the integer kept internal for foreign keys.
- **SQL injection:** I required the search to withstand SQLi even with obfuscation.
  This was implemented with the SQLAlchemy ORM using **bound parameters** plus
  **LIKE-wildcard escaping**, and verified against injection payloads
  (`' OR '1'='1`, `'; DROP TABLE …`, `%`, `_`) so they resolve as literal text.
- **File-upload attack prevention:** I required blocking shell/polyglot uploads
  even when the extension and Content-Type are forged. The validator was hardened
  beyond magic-byte sniffing to **deep-validate** each type (full Pillow decode for
  images, `%PDF-` marker for PDFs, strict UTF-8 for text), and store bytes under an
  opaque key in a private bucket.
- **Frontend layout:** I directed a **three-panel master-detail redesign**
  (Versions on the left, selected-version Detail in the middle, Search on the
  right) with a fixed-layout toolbar (custom Browse button, mandatory Title,
  ellipsis filename, reserved status slot), iterating on the specifics until it
  matched the intended UX.

In short: the AI accelerated implementation and test-writing; the architecture,
security requirements, and design decisions were mine, reviewed at each step.

---

## Implemented vs. not implemented

**Implemented (obligatory):** email + strong-password auth (JWT, persistent
session), per-user upload/list/download/delete with strict 404 isolation, upload
validation (10 MB, type whitelist, deep anti-forgery), upload progress/success/
error feedback, MySQL metadata + MinIO objects, one-command Docker, backend tests.

**Implemented (bonus):** streamed downloads, image thumbnails (incl. per-version),
owner-scoped search, HTTP thumbnail caching (ETag/304), file **versioning**
(history, per-version download/thumbnail/description, contiguous renumbering on
delete), MinIO/S3 storage, expiring presigned links (`/media/{id}/link`, API), and
a one-command public **deploy** via Cloudflare Tunnel (see Deploy below).

**Not implemented:**
- **Expiring-link UI button** — the endpoint exists and works; it isn't currently
  surfaced in the redesigned UI.
- **OTP / 2FA** — intentionally out of scope: not in the test's requirements or
  bonus list; an email-dependent gate adds risk for no scoring benefit. The
  architecture supports adding it later (a `services/email.py` + a one-time-codes
  table).

---

## Tests

55 backend tests (pytest) cover auth, validation, per-user isolation, injection
safety, versioning (incl. renumbering/repointing), and error handling:

```bash
docker compose run --rm backend python -m pytest app/tests -q
```

---

## Deploy (public HTTPS demo — Cloudflare Tunnel)

Run the production stack (static frontend served by Caddy + `/api` reverse proxy)
and expose it over a free public HTTPS URL — no VPS, domain, or account needed:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

Then grab the URL from the tunnel logs:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs cloudflared
# -> https://<random>.trycloudflare.com
```

In production the frontend is a static build and the API is served on the same
origin under `/api` (no CORS). Cloudflare terminates TLS at its edge; the tunnel
is outbound-only and exposes only the app — not the host, database, or MinIO.
Stop the stack to take it offline. (Quick tunnels are ephemeral; the URL changes
on each restart. A stable URL needs a free Cloudflare account + named tunnel.)

**Access gate.** The deployed UI is protected by HTTP Basic auth so only
evaluators (who have this README) can load it, even if the URL leaks:

- **Username:** `evaluator`  ·  **Password:** `c4gRZ@P1x3lBr33ders!`

Only the frontend is gated; `/api` stays protected by the app's own JWT auth
(Basic and Bearer would collide on the `Authorization` header). To change the
password, regenerate a bcrypt hash and replace it in `deploy/Caddyfile`:

```bash
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'your-new-password'
```
