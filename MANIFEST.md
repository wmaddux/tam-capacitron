# Project manifest (for new agents / onboarding)

Use this file to orient a new agent or developer when starting work on **tam-capacitron**. Read it first, then open the referenced docs and code as needed.

---

## What this project is

**tam-capacitron** is a dynamic Aerospike capacity planning tool. Users adjust inputs (topology, memory, workload, resilience) via an intuitive UI (sliders/knobs); the app computes utilization and performance estimates in real time. Features include: Load from defaults, Load from collectinfo (bundle), Export to a standard JSON file, and (planned) save/compare states and Load from output file.

**Current scope:** Multi-namespace supported. UI has Cluster card + Namespaces cards (Add/Remove); state is `{ cluster, namespaces[] }`. Compute uses **POST /api/compute-v2**; Load from collectinfo returns `cluster` + `namespaces`. Total memory used base = Primary Index Shmem (64 bytes per replicated object) + Secondary Index Shmem (collectinfo-style).

**Tech stack:** Web app (HTML/JS front-end) + Python backend (FastAPI). Formulas live in Python (human-readable); no spreadsheet cell references in code.

---

## Repository and docs

| Item | Location | Purpose |
|------|----------|---------|
| Design plan | [PLAN.md](PLAN.md) | Full design, phases 0–5, architecture, UX, future work |
| Calculation catalog | [docs/CALCULATION_CATALOG.md](docs/CALCULATION_CATALOG.md) | Mapping of all calculations to spreadsheet cells (capacity planner + Sizing Estimator); cell refs live here only |
| **Collectinfo input mapping** | [docs/COLLECTINFO_INPUT_MAPPING.md](docs/COLLECTINFO_INPUT_MAPPING.md) | Which CapacityInputs come direct from collectinfo vs calculated; ingestor output contract for Phase 3 |
| Strawman UI/flow | [docs/STRAWMAN_UI_AND_FLOW.md](docs/STRAWMAN_UI_AND_FLOW.md) | Wireframes and process flow for the single-screen app |
| **Chosen wireframe** | [docs/mockups/mockup-cluster-namespace-split-with-definition.html](docs/mockups/mockup-cluster-namespace-split-with-definition.html) | Reference for UI: three-column (Inputs \| Outputs \| Definition), Cluster + Namespaces cards, param help on label click; **implemented** in app/static/index.html |
| **Multi-namespace API** | [docs/API_MULTI_NAMESPACE.md](docs/API_MULTI_NAMESPACE.md) | Request/response for POST /api/compute-v2 (cluster + namespaces); aggregation rules |
| **Testing multi-namespace** | [docs/TESTING_MULTI_NAMESPACE.md](docs/TESTING_MULTI_NAMESPACE.md) | How to test compute-v2 and multi-namespace aggregation |
| Session log | [docs/SESSION_LOG.md](docs/SESSION_LOG.md) | Per-session log of work done; update at end of each context session |
| Contributing / CM | [CONTRIBUTING.md](CONTRIBUTING.md) | Branch naming, commit and tag policy, push workflow |

---

## Key code and assets

| Area | Path | Notes |
|------|------|-------|
| Input/output model | [core/model.py](core/model.py) | `ClusterInputs`, `NamespaceInputs`, `CapacityInputs`, `CapacityOutputs`, `get_default_inputs()`; device_size_gb default 50 |
| Formulas | [core/formulas.py](core/formulas.py) | All capacity formulas; `primary_index_shmem_gb`, `secondary_index_shmem_gb`, `total_memory_used_base_gb` = Primary + SI Shmem (see catalog) |
| Engine | [core/engine.py](core/engine.py) | `run_multi(cluster, namespaces)` aggregates per-namespace; `run(inp)` legacy flat → cluster + one namespace |
| API + static UI | [app/main.py](app/main.py), [app/static/index.html](app/static/index.html) | FastAPI: `/`, `/api/defaults`, `/api/compute`, **/api/compute-v2**, `/api/load-collectinfo`; three-column UI, cluster + namespaces state, Load from defaults/collectinfo, Export |
| Tests | [tests/](tests/) | `test_engine.py`, `test_api_compute_v2.py`, etc.; run with `PYTHONPATH=. python -m pytest tests/ -v` from repo root |
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

- **Multi-namespace** is implemented: cluster + list of namespaces; UI has Add/Remove namespace, at least one namespace required.
- **No cell references** (e.g. `calcManual!C9`) in application code; use [docs/CALCULATION_CATALOG.md](docs/CALCULATION_CATALOG.md) for traceability.
- **Total memory used base** = Primary Index Shmem (64 B per replicated object) + Secondary Index Shmem (SI constants in formulas.py).
- Collectinfo ingestion returns `cluster` + `namespaces` (and legacy flat for compatibility); sample bundle: `bundles/fidelity-case00044090-20250226.zip` (when present).

---

## After a session

Update [docs/SESSION_LOG.md](docs/SESSION_LOG.md) with: date/session id, summary of work, files changed, and any decisions or follow-ups. This keeps context for the next agent or session.
