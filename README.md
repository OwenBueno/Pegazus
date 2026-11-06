# Pegazus (P0–P5 lite)

Local Docker monorepo: Next.js + FastAPI + Supabase Auth/DB.

## Prerequisites

- Docker Desktop
- Supabase CLI — this repo ships one at [`.tools/supabase/supabase.exe`](.tools/supabase/supabase.exe)

## First run

```powershell
copy .env.example .env
supabase start
supabase db reset   # applies migrations + seed (bootstrap only)
docker compose up --build
```

Existing database: `supabase migration up` applies new migrations without a reset. If it re-runs an old one ("already exists"), that migration was applied by hand: record it with `supabase migration repair --local --status applied <version>`, then rerun.

- App: http://localhost:3000
- API: http://localhost:8000/health
- Grafana (OTel LGTM): http://localhost:3001

## Features (lite)

| Slice | Behavior |
| --- | --- |
| Any subject | AI infers a **subject profile** (math, language, science, humanities, code…) the learner confirms in the wizard |
| Path create | Wizard: goal → profile → optional exam (recommended) → files/corpus → **outline-only** plan |
| Lazy content | On prepare: primer + ≥5 items + **lesson_beats** + cached GenUI plan |
| Lesson runner | AI-composed beats; left lesson rail; topic-true practice items |
| Prefetch | Opening skill N materializes N+1 in background; first skill auto-starts after outline |
| Rematerialize | Re-open / rematerialize a skill to refresh items + beats after generator changes |
| Practice | Server-side **grader registry** (SymPy, choice, match, order, cloze, numeric+units, rubric LLM, speech, code tests); answer keys never sent to the client; FSRS (PARTIAL → Hard) |
| GenUI catalog | Role × category library: math (step editor, plotter…), core (QuickCheck, Cloze, FreeResponse…), humanities (Timeline, SourceExcerpt), language (Flashcards, TTS, pronunciation), science (ChemFormula, units), code (Pyodide / JS worker) |
| Citations | Non-math lessons are web-researched; each lesson lists its sources and **only cited URLs** are ever rendered |
| Ask | `/ask` Quick Socratic — max 3 exchanges; no FSRS/path writes |
| Research serve | Nodes need **≥5 VERIFIED** items before practice/diagnostic |
| Diagnostic | KST only on materialised nodes; exam can seed initial mastery hints |
| Consent / BYO / Offline | As before; AI or BYO key required to build a path |
| Observability | FastAPI → OTLP → `otel-lgtm` (Grafana :3001) |

## Seed & corpus

- Algebra seed remains in DB for local schema/tests only — **new user paths do not attach seed nodes**.
- Corpus Markdown under `corpus/` used when “deep research” is enabled on create.
- Apply seed: `docker compose run --rm -v ${PWD}/supabase:/supabase:ro api python scripts/apply_seed.py`

## Tests & benches

```powershell
docker compose exec -T api python -m pytest -q <files>   # not the whole suite: one test hangs
docker compose exec web npx tsc --noEmit
```

## Roadmap

- **Done:** multi-subject migration ([Doc 10](docs/10-multi-subject-spec.md), tickets MS-1.1 … MS-5.3 in [Doc 11](docs/11-multi-subject-execution-plan.md)).
- **Next:** KPI pilot, server code sandbox, phoneme-level speech feedback, AI image generation (see [Doc 08 P6](docs/08-delivery-phases.md)).

## Deferred

Syllabus PDF long-term storage / virus scan, full 20×10 bank, KPI pilot, real guardian IdP, cloud KMS, Celery, unbounded web scrape.

## Notes

- Sign-in is **email OTP** locally (Mailpit).
- RestOverlay stays a page overlay (not a GenUI registry widget).
- Package name for FSRS-6 is `fsrs` on PyPI.
