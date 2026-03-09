# Project manifest (for new agents / onboarding)

Use this file to orient a new agent or developer when starting work on **tam-capacitron**. Read it first, then open the referenced docs and code as needed.

---

## What this project is

**tam-capacitron** is a dynamic Aerospike capacity planning tool. Users adjust inputs (topology, memory, workload, resilience) via an intuitive UI (sliders/knobs); the app computes utilization and performance estimates in real time. Features include: Load from defaults, Load from collectinfo (bundle), Export to a standard JSON file, and (planned) save/compare states and Load from output file.

**Current scope:** One namespace, one cluster. Future: multiple namespaces per cluster.

**Tech stack:** Web app (HTML/JS front-end) + Python backend (FastAPI). Formulas live in Python (human-readable); no spreadsheet cell references in code.

---

## Repository and docs

| Item | Location | Purpose |
|------|----------|---------|
| Design plan | [PLAN.md](PLAN.md) | Full design, phases 0–5, architecture, UX, future work |
| Calculation catalog | [docs/CALCULATION_CATALOG.md](docs/CALCULATION_CATALOG.md) | Mapping of all calculations to spreadsheet cells (capacity planner + Sizing Estimator); cell refs live here only |
| **Collectinfo input mapping** | [docs/COLLECTINFO_INPUT_MAPPING.md](docs/COLLECTINFO_INPUT_MAPPING.md) | Which CapacityInputs come direct from collectinfo vs calculated; ingestor output contract for Phase 3 |
| Strawman UI/flow | [docs/STRAWMAN_UI_AND_FLOW.md](docs/STRAWMAN_UI_AND_FLOW.md) | Wireframes and process flow for the single-screen app |
| **Chosen wireframe** | [docs/mockups/mockup-cluster-namespace-split-with-definition.html](docs/mockups/mockup-cluster-namespace-split-with-definition.html) | **Reference for UI implementation:** three-column layout (Inputs | Outputs | Definition), Cluster + Namespaces cards, parameter help on label click; implement app UI from this mockup |
| Session log | [docs/SESSION_LOG.md](docs/SESSION_LOG.md) | Per-session log of work done; update at end of each context session |
| Contributing / CM | [CONTRIBUTING.md](CONTRIBUTING.md) | Branch naming, commit and tag policy, push workflow |

---

## Key code and assets

| Area | Path | Notes |
|------|------|-------|
| Input/output model | [core/model.py](core/model.py) | `CapacityInputs`, `CapacityOutputs`, `get_default_inputs()`; defaults are minimum safe values |
| Formulas | [core/formulas.py](core/formulas.py) | All capacity formulas; business-language only (see catalog for cell mapping) |
| Engine | [core/engine.py](core/engine.py) | `run(inp)` → evaluates in dependency order, returns `CapacityOutputs` |
| API + static UI | [app/main.py](app/main.py), [app/static/index.html](app/static/index.html) | FastAPI: `/`, `/api/defaults`, `/api/compute`; single-page UI with sliders and immediate reactivity |
| Tests | [tests/test_engine.py](tests/test_engine.py) | Engine tests; run with `python -m pytest tests/` from repo root |
| Workbook sources | [Capacity_planner_v3.0-fidelity_workbench.xlsx](Capacity_planner_v3.0-fidelity_workbench.xlsx), [Tool_Aerospike_Sizing_Estimator_(10_14).xlsx](Tool_Aerospike_Sizing_Estimator_(10_14).xlsx) | Do not embed cell refs in code; use [docs/CALCULATION_CATALOG.md](docs/CALCULATION_CATALOG.md) for mapping |

---

## How to run

```bash
cd /path/to/tam-capacitron
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload
# Open http://127.0.0.1:8000
```

Run tests: `PYTHONPATH=. python -m pytest tests/ -v`

---

## Scope and constraints

- **One namespace, one cluster** for now; design with future multi-namespace in mind.
- **No cell references** (e.g. `calcManual!C9`) in application code; use [docs/CALCULATION_CATALOG.md](docs/CALCULATION_CATALOG.md) for traceability.
- Collectinfo ingestion will reuse **citrusleaf/tam-tools** (tam-flash-report); sample bundle: `bundles/fidelity-case00044090-20250226.zip` (when present).

---

## After a session

Update [docs/SESSION_LOG.md](docs/SESSION_LOG.md) with: date/session id, summary of work, files changed, and any decisions or follow-ups. This keeps context for the next agent or session.
