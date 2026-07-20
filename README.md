# PRism

**AI PR Reviewer + Regression Triage.**

PRism analyzes GitHub pull requests: it parses the diff, classifies risk with
deterministic heuristics, asks an LLM for a structured review (summary, 1–5 risk
score, top concerns, suggested regression tests, likely regression areas), stores
every analysis, and surfaces similar historical PRs. See
[`docs/technical-design.md`](docs/technical-design.md) for the full design.

> **Status: Milestone 1 — project skeleton.** Backend (FastAPI health check +
> config + structured logging), frontend (Next.js landing + dashboard placeholder),
> database config, tests, and dev tooling are in place. The analysis pipeline lands
> in later milestones.

---

## Stack

| Part      | Tech |
|-----------|------|
| Backend   | Python 3.11+ (developed on 3.12), FastAPI, Pydantic v2, pydantic-settings |
| Frontend  | Next.js (App Router) + TypeScript |
| Database  | PostgreSQL 16 + pgvector (via Docker) |
| Tooling   | pip + PEP 621 `pyproject.toml`, ruff, mypy, pytest; npm, ESLint, tsc |

> **Note on packaging:** the design doc names Poetry; this repo uses a standard
> PEP 621 `pyproject.toml` installed with `pip` (works with Poetry 2.x too), so no
> Poetry install is required.

---

## Prerequisites

- Python 3.11+ (3.12 recommended)
- Node.js 20+ (developed on 26) and npm
- Docker (for local Postgres) — optional for Milestone 1, since the health check
  needs no database

---

## Quick start

```bash
# 1. Clone and enter
git clone https://github.com/anshbabar/PRism.git
cd PRism

# 2. Config
cp .env.example .env        # defaults work out of the box for local dev

# 3. Backend
make install                # creates .venv and installs backend deps
make test                   # run backend tests
make dev                    # serve API at http://localhost:8000  (try /health)

# 4. Frontend (separate terminal)
make web-install
make web                    # serve dashboard at http://localhost:3000

# 5. Database (optional in Milestone 1)
make db-up                  # start Postgres+pgvector; make db-down to stop
```

Backend API docs (Swagger) are auto-served at `http://localhost:8000/docs`.

---

## Make targets

Run `make help` for the full list. The common ones:

| Command        | What it does |
|----------------|--------------|
| `make dev`     | Run the backend API with autoreload |
| `make web`     | Run the Next.js dev server |
| `make test`    | Run backend tests (pytest) |
| `make lint`    | Lint backend (ruff) and frontend (eslint) |
| `make typecheck` | Type-check backend (mypy) and frontend (tsc) |
| `make eval`    | Run the eval harness (stub until Milestone 6) |
| `make db-up` / `make db-down` | Start / stop the Postgres container |
| `make fmt`     | Auto-format backend code |

---

## Layout

```
app/            FastAPI backend (api/, core/)
tests/          Backend tests (pytest)
web/            Next.js + TypeScript frontend (app/, lib/)
docs/           Technical design document
.github/        CI workflow
docker-compose.yml   Postgres 16 + pgvector
```

---

## CI

GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs on
every push and PR:

- **Backend:** ruff lint + format check, mypy, pytest, and an eval smoke test.
- **Frontend:** `tsc --noEmit` type-check and ESLint.

---

## License

MIT — see [`LICENSE`](LICENSE).
