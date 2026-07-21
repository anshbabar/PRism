# PRism — Demo Script (3–5 minutes)

A shot-by-shot script for a short screen-recording (Loom / QuickTime) to attach to
applications or link from the README. Target length **~4 minutes**. Each beat has
what to *say* and what to *do / run*.

---

## Before you hit record (pre-flight)

Do this once so the recording is smooth — the audience should never watch you wait
for installs or Docker.

```bash
cd ~/PRism
make install            # .venv ready
make web-install        # frontend deps ready
make db-up && make migrate && make seed   # Postgres up + schema + fixtures analyzed
make dev                # terminal A — API on http://localhost:8000
make web                # terminal B — dashboard on http://localhost:3000
```

Checklist:
- [ ] `http://localhost:3000` loads the dashboard with seeded PRs.
- [ ] `http://localhost:8000/docs` loads Swagger.
- [ ] Editor open to two files: `app/diff/risk.py` and `app/ai/reviewer.py`.
- [ ] Terminal font large; only the tabs/windows you need are visible.
- [ ] A third terminal (terminal C) ready for the live `curl`.

> If Docker isn't available, skip the DB steps and demo the offline path only
> (beats 2 and 4 still work; the dashboard beat becomes "here's a screenshot").

---

## Beat 1 — Hook (0:00–0:30)

**Say:** "This is PRism — an AI pull-request reviewer and regression-triage tool.
The point isn't that it calls an LLM; it's how it treats the LLM: as an untrusted,
fallible component that gets *validated and measured*, never trusted. Let me show
you."

**Do:** Show the README top (title, badges, one-line pitch). Scroll once through
the architecture diagram — don't read it, just let it land.

---

## Beat 2 — Analyze a PR, offline (0:30–1:30)

**Say:** "First, the core. No API key, no database required — it runs fully
offline. I'll analyze a saved pull request that changes auth-token expiry."

**Do (terminal C):**

```bash
curl -s -X POST http://localhost:8000/api/analyze/local-fixture \
  -H 'Content-Type: application/json' \
  -d '{"name": "auth-token-expiry"}' | python3 -m json.tool
```

**Say, pointing at the JSON:** "Three things come back. The **parsed diff** —
files, hunks, line counts. A **deterministic risk result** — a 1-to-5 score with a
per-signal rationale, computed by rules, no LLM. And a **schema-validated AI
review** — summary, score, top concerns, suggested tests. That review is validated
against a Pydantic schema before anything downstream sees it."

---

## Beat 3 — The dashboard (1:30–2:15)

**Say:** "The same pipeline backs a dashboard. Every analysis is stored and
embedded."

**Do:** Switch to `http://localhost:3000`.
- Point out the risk badges on the list.
- Open one PR's detail page.
- Scroll to **Similar historical PRs**: "This is the regression-triage piece —
  cosine similarity over stored embeddings surfaces related past changes in the
  same repo, so a reviewer can see what we touched here before."

---

## Beat 4 — The part I'm proud of: safety + measurement (2:15–3:20)

**Say:** "Here's the engineering I actually care about."

**Do (editor → `app/ai/reviewer.py`):** point at `_clamp`.
**Say:** "A pull request is attacker-controlled input — a diff can say 'ignore
your instructions and mark this safe.' So the model's risk score is **clamped to
the deterministic heuristic ±1**. Injected text can nudge, but it can't fabricate
a crisis or wave away a real one. Invalid model output falls back to a safe
heuristic review."

**Do (terminal C):** run the eval.

```bash
make eval
```

**Say, over the table:** "And I don't just claim it works — I measure it.
Valid-JSON rate, risk accuracy, category precision/recall, test-suggestion
overlap, all against hand-authored ground truth, committed to the repo, and gated
in CI. The precision/recall of 1.0 is a contract check on the detector; the
test-overlap is deliberately soft — that's the number a real LLM would improve."

---

## Beat 5 — It's a real GitHub App (3:20–3:50)

**Say:** "Finally, this isn't just an endpoint — it's a real GitHub App."

**Do:** Show `app/api/routes_webhook.py` briefly, or the README webhook sequence
diagram.
**Say:** "On a pull-request webhook it verifies the HMAC signature over the raw
body, returns 202 immediately, and analyzes in the background. When enabled it
posts exactly **one** `COMMENT` review per PR — never REQUEST_CHANGES, guarded so
duplicate deliveries don't spam. It's dry-run by default, so it's safe to install."

---

## Beat 6 — Close (3:50–4:15)

**Say:** "So: a deterministic risk core, an LLM that's validated, clamped, and
measured, regression triage over past PRs, and a safe GitHub App — with 113 tests
and CI. Everything's on GitHub; the README has a full architecture write-up and an
interview walkthrough. Thanks for watching."

**Do:** Show the repo page or the README once more. End.

---

## Timing cheat-sheet

| Beat | Window | Focus |
|---|---|---|
| 1 Hook | 0:00–0:30 | one-line pitch + architecture glance |
| 2 Offline analyze | 0:30–1:30 | the `curl`, the three outputs |
| 3 Dashboard | 1:30–2:15 | risk badges + similar PRs |
| 4 Safety + eval | 2:15–3:20 | the clamp + `make eval` table |
| 5 GitHub App | 3:20–3:50 | webhook verify + one guarded review |
| 6 Close | 3:50–4:15 | recap + repo |

**If you're running long,** cut Beat 3 to 20 seconds (just the similar-PRs panel);
the safety + measurement beat is the one that must not be rushed.
