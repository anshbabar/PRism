# PRism

**AI PR Reviewer + Regression Triage.**

PRism analyzes GitHub pull requests: it parses the diff, classifies risk with
deterministic heuristics, asks an LLM for a structured review (summary, 1–5 risk
score, top concerns, suggested regression tests, likely regression areas), stores
every analysis, and surfaces similar historical PRs. See
[`docs/technical-design.md`](docs/technical-design.md) for the full design.

> **Status: Milestone 4 — evaluation harness.** On top of diff parsing,
> rule-based risk, and schema-validated AI review, PRism now ships a reproducible
> **evaluation harness**: `make eval` runs the full pipeline over every benchmark
> fixture, computes quality metrics (valid-JSON rate, risk-score accuracy,
> category precision/recall, test-suggestion overlap, latency), writes
> `eval/results/latest.json`, and prints a summary table. It runs offline with the
> **mock provider** by default (also the CI smoke test); set
> `LLM_PROVIDER=anthropic` (+ `ANTHROPIC_API_KEY`) for the real Claude provider.
> Persistence and retrieval land in later milestones.

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
| `make eval`    | Run the evaluation harness (mock provider) + write `eval/results/latest.json` |
| `make db-up` / `make db-down` | Start / stop the Postgres container |
| `make fmt`     | Auto-format backend code |

---

## Local fixture analysis (Milestone 2)

PRism can analyze saved PR fixtures with no GitHub App and no network — the
offline demo path. Fixtures live in `eval/fixtures/sample_prs/<name>/`, each with
`metadata.json`, `diff.patch`, and `expected.json`.

**Available fixtures:** `auth-token-expiry`, `add-orders-table`,
`bump-dependencies`, `remove-legacy-tests`, `update-env-config`,
`add-orders-api-endpoint`, `large-refactor-logging`.

Start the API, then call the endpoint with a fixture name:

```bash
make dev   # http://localhost:8000

curl -s -X POST http://localhost:8000/api/analyze/local-fixture \
  -H 'Content-Type: application/json' \
  -d '{"name": "add-orders-table"}' | python3 -m json.tool
```

The response contains the **parsed diff** (files, hunks, changed line ranges,
add/delete counts, extension, `is_test`) and a **risk result**:

```jsonc
{
  "name": "add-orders-table",
  "metadata": { "...": "..." },
  "parsed_diff": { "files_changed": 2, "total_additions": 15, "files": [ ... ] },
  "risk": {
    "score": 4,
    "band": "high",
    "signals": [
      { "category": "db_schema", "severity": 3, "file_path": "migrations/0003_add_orders.sql", "detail": "..." },
      { "category": "missing_tests", "severity": 2, "file_path": null, "detail": "..." }
    ],
    "rationale": "Risk 4/5 (high). Signals: db_schema, missing_tests."
  }
}
```

**Risk categories** (deterministic, no LLM): `auth`, `db_schema`, `api_route`,
`dependency`, `config_env`, `missing_tests`, `large_diff`, `test_removed`.
Invalid fixture names return 400; unknown names return 404.

The response also includes an `ai` object with a schema-validated review:

```jsonc
"ai": {
  "status": "completed",          // or "fallback" if model output was invalid
  "provider": "mock",             // "anthropic" when LLM_PROVIDER=anthropic
  "model": "mock",
  "review": {
    "summary": "...",
    "risk_score": 4,              // clamped to the heuristic score +/- 1
    "risk_categories": ["db_schema", "missing_tests"],
    "top_concerns": [ { "title": "...", "detail": "..." } ],   // <= 5
    "suggested_tests": [ { "area": "...", "reason": "..." } ],
    "regression_risks": ["..."],
    "github_review_markdown": "### PRism review ..."
  }
}
```

**AI provider.** `LLM_PROVIDER=mock` (default) is deterministic and offline — no
key needed, used in tests/CI. `LLM_PROVIDER=anthropic` calls Claude via the
`anthropic` SDK using structured outputs; set `ANTHROPIC_API_KEY` and (optionally)
`LLM_MODEL`. All PR content is treated as untrusted input: the prompt defends
against injection, output is schema-validated, and the risk score is clamped to
the deterministic heuristic score so a malicious diff can't force it.

Interactive docs for the endpoint: `http://localhost:8000/docs`.

---

## Evaluation harness (Milestone 4)

PRism is *measured*, not vibes. The harness runs the full analysis pipeline
(`parse → risk → AI review`) over every fixture in `eval/fixtures/sample_prs/`,
compares the output against each fixture's `expected.json`, and reports quality
metrics.

```bash
make eval                                  # mock provider + invariant checks (what CI runs)
./.venv/bin/python eval/run_eval.py        # same, without the smoke-test gate
./.venv/bin/python eval/run_eval.py --provider anthropic   # score the live Claude provider
```

Each run writes **`eval/results/latest.json`** (aggregate metrics + a per-fixture
breakdown) and prints a summary table. The reusable logic lives in `app/eval/`
(`metrics.py` = pure formulas, `runner.py` = orchestration); `eval/run_eval.py`
is a thin CLI wrapper.

**Ground truth.** Each fixture's `expected.json` carries `expected_categories`
(the risk categories that should fire), `risk_band` (`low`/`medium`/`high`), and
`expected_test_areas` (test topics a reviewer would want).

### What each metric means

| Metric | Meaning | Formula |
|---|---|---|
| `valid_json_rate` | How often the **primary** provider produced schema-valid output (heuristic fallbacks excluded). | `#{completed} / #fixtures` |
| `risk_score_accuracy_within_1` | Whether the final (clamped) risk score lands within 1 of the expected band. | band → canonical score (`low=2, medium=3, high=4`); pass if `abs(predicted − canonical) ≤ 1` |
| `risk_category_precision` | Of the categories the review flagged, how many were expected (micro-averaged). | `TP / (TP + FP)` |
| `risk_category_recall` | Of the expected categories, how many the review flagged (micro-averaged). | `TP / (TP + FN)` |
| `suggested_test_overlap` | How well suggested test areas cover the expected ones. | per expected area, best token-Jaccard vs any suggestion; averaged |
| `average_latency_ms` | Mean per-fixture pipeline wall-time. | `mean(latency_ms)` |

`suggested_test_overlap` tokenizes each area (lowercase `[a-z0-9]+`, minus a small
stopword set and 1-char tokens) and uses Jaccard similarity `|A∩B| / |A∪B|`.

### Current benchmark results

Seven fixtures, **mock provider** (offline, deterministic — the CI-tested path):

| Metric | Result |
|---|---|
| `valid_json_rate` | **1.00** |
| `risk_score_accuracy_within_1` | **1.00** |
| `risk_category_precision` | **1.00** |
| `risk_category_recall` | **1.00** |
| `suggested_test_overlap` | **0.54** |
| `average_latency_ms` | **< 1 ms** (deterministic-only; machine-dependent) |

Notes on interpreting these:

- Precision/recall of **1.00** is expected and honest: the fixtures'
  `expected_categories` are authored against the deterministic detector contract,
  so this confirms the detector matches its spec across the set (the
  `test_fixture_matches_expected` test enforces the same equality).
- `suggested_test_overlap` is intentionally a **soft** metric at **~0.54**: the
  offline mock suggests one generic area per category, so it partially — not
  fully — covers the specific expected areas. A live LLM (`--provider anthropic`)
  is expected to score higher; this is the metric that most rewards the real model.

The committed `eval/results/latest.json` lets a reviewer see the numbers without
running anything. `make eval` also enforces smoke-test invariants (≥ 5 fixtures,
and `valid_json_rate == 1.0` under the mock provider) and exits non-zero on
regression — this is the CI eval gate.

---

## Layout

```
app/            FastAPI backend
  api/          routes (health, analyze)
  core/         config + structured logging
  diff/         unified-diff parser + rule-based risk heuristics
  ai/           LLM provider abstraction, review schema, prompts, fallback
  eval/         evaluation metrics (formulas) + harness runner
  ingest/       local PR fixture loader
tests/          Backend tests (pytest), incl. tests/eval/
web/            Next.js + TypeScript frontend (app/, lib/)
docs/           Technical design document
eval/
  run_eval.py   evaluation harness CLI
  fixtures/     sample PR fixtures (sample_prs/)
  results/      latest.json (committed benchmark output)
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
