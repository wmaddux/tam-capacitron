# Project manifest (for new agents / onboarding)

Use this file to orient a new agent or developer when starting work on **tam-capacitron**. Read it first, then open the referenced docs and code as needed.

---

## What this project is

**tam-capacitron** is a dynamic Aerospike capacity planning tool. Users adjust inputs (topology, memory, workload, resilience) via an intuitive UI (sliders/knobs); the app computes utilization and performance estimates in real time. Features include: Load from defaults, Load from collectinfo (bundle), Export to a standard JSON file, and (planned) save/compare states and Load from output file.

**Current scope:** Multi-namespace supported. UI has Cluster card with **Server instance specs** (vCPUs, RAM (GB), Storage, Networking in a box—for mapping cloud instance types; only RAM affects calculations), default storage pattern, then topology (nodes, devices, device size), overhead %, and a divider before Nodes lost. Namespaces cards (Add/Remove) with storage pattern (HMA/In-Memory/All Flash/DMD/Custom), Custom placement, compression, and capacity thresholds. State includes `cluster.vcpus`, `cluster.instance_storage`, `cluster.instance_networking`. **Defaults and sliders** come from [config/inputs.json](config/inputs.json); UI fetches **GET /api/input-config** on load. Column 3: Parameter help (click param label) + **Show my work** (Storage, Memory, and Failure sections with step-by-step formulas and separators). Outputs: numbers with thousand separators; Storage shows Data stored (TB) and Device total storage (TB); redundant Total available storage row removed. Compute uses **POST /api/compute-v2**. [docs/CALCULATIONS.md](docs/CALCULATIONS.md) is the source of truth for capacity formulas; SI cushion 16 MiB. **Collectinfo load:** Bundles .zip/.tgz/.tar; Device Total TB/GB; no-device namespaces get In-Memory (MMM), 0 device storage; derivation script [tests/test_collectinfo_derivations.sh](tests/test_collectinfo_derivations.sh); [scripts/gather_asadm_for_calculations.sh](scripts/gather_asadm_for_calculations.sh).

**Tech stack:** Web app (HTML/JS front-end) + Python backend (FastAPI). Formulas live in Python (human-readable); no spreadsheet cell references in code.

---

## Repository and docs

| Item | Location | Purpose |
|------|----------|---------|
| Design plan | [PLAN.md](PLAN.md) | Full design, phases 0–5, architecture, UX, future work |
| Calculation catalog | [docs/CALCULATION_CATALOG.md](docs/CALCULATION_CATALOG.md) | Mapping of all calculations to spreadsheet cells (capacity planner + Sizing Estimator); cell refs live here only |
| **Calculations** | [docs/CALCULATIONS.md](docs/CALCULATIONS.md) | Lists all capacity calculations by output and input situation per model docs (storage util, memory util, cluster-only, failure) |
| **Process redesign (UI compute)** | [docs/PROCESS_REDESIGN_UI_COMPUTE.md](docs/PROCESS_REDESIGN_UI_COMPUTE.md) | How UI computes Storage % and Memory % from all input combinations; aligns model docs, derivations script, API, engine, and ingest |
| **Model: Storage util** | [docs/model_calculation_storage_util.md](docs/model_calculation_storage_util.md) | Pseudo-code for Storage utilization %; collectinfo derivations for inputs |
| **Model: Memory util** | [docs/model_calculation_mem_util.md](docs/model_calculation_mem_util.md) | Pseudo-code for Memory utilization %; collectinfo derivations for inputs |
| **Collectinfo input mapping** | [docs/COLLECTINFO_INPUT_MAPPING.md](docs/COLLECTINFO_INPUT_MAPPING.md) | Which CapacityInputs come direct from collectinfo vs calculated; ingestor output contract for Phase 3 |
| Strawman UI/flow | [docs/STRAWMAN_UI_AND_FLOW.md](docs/STRAWMAN_UI_AND_FLOW.md) | Wireframes and process flow for the single-screen app |
| **Input config** | [config/inputs.json](config/inputs.json), [app/config.py](app/config.py) | Defaults and slider min/max/step; single place to edit. See [config/README.md](config/README.md). API: **GET /api/input-config** (defaults + schema). |
| **UI reference** | [docs/mockups/](docs/mockups/) | **Current app** ([app/static/index.html](app/static/index.html)): three-column (Inputs \| Outputs \| Parameter help + Show my work). Cluster: Server instance specs (vCPUs, RAM, Storage, Networking) in a box, then topology, divider, Nodes lost. Namespaces: pattern pills, Custom placement, compression, capacity thresholds. Show my work: Storage, Memory, Failure sections. Param help on label click; Load from collectinfo "Loading…". |
| **Multi-namespace API** | [docs/API_MULTI_NAMESPACE.md](docs/API_MULTI_NAMESPACE.md) | Request/response for POST /api/compute-v2 (cluster + namespaces); aggregation rules |
| **Testing multi-namespace** | [docs/TESTING_MULTI_NAMESPACE.md](docs/TESTING_MULTI_NAMESPACE.md) | How to test compute-v2 and multi-namespace aggregation |
| Session log | [docs/SESSION_LOG.md](docs/SESSION_LOG.md) | Per-session log of work done; update at end of each context session |
| Contributing / CM | [CONTRIBUTING.md](CONTRIBUTING.md) | Branch naming, commit and tag policy, push workflow |

---

## Key code and assets

| Area | Path | Notes |
|------|------|-------|
| Input/output model | [core/model.py](core/model.py) | `ClusterInputs` (includes `vcpus`, `instance_storage`, `instance_networking` for instance specs), `NamespaceInputs`, `CapacityInputs`, `CapacityOutputs`; `get_default_inputs()` from config |
| Config loader | [app/config.py](app/config.py) | Loads [config/inputs.json](config/inputs.json); `get_defaults()`, `get_slider_specs()` |
| Formulas | [core/formulas.py](core/formulas.py) | All capacity formulas; SI cushion 16 MiB; Primary + SI Shmem (see [docs/CALCULATIONS.md](docs/CALCULATIONS.md)) |
| Engine | [core/engine.py](core/engine.py) | `run_multi(cluster, namespaces)` aggregates per-namespace; `run(inp)` legacy flat → cluster + one namespace |
| API + static UI | [app/main.py](app/main.py), [app/static/index.html](app/static/index.html) | FastAPI: `/`, `/api/defaults`, **/api/input-config**, `/api/compute`, **/api/compute-v2**, `/api/load-collectinfo`, `/api/schema`; UI fetches input-config on load; Server instance specs in Cluster; Show my work (Storage, Memory, Failure) |
| Tests | [tests/](tests/) | `test_engine.py`, `test_api_compute_v2.py`, `test_asadm_ingest.py`, `test_mapping.py`, etc.; run with `PYTHONPATH=. python -m pytest tests/ -v` from repo root. [tests/test_collectinfo_derivations.sh](tests/test_collectinfo_derivations.sh) runs Storage/Memory derivations against a bundle (requires asadm). [scripts/gather_asadm_for_calculations.sh](scripts/gather_asadm_for_calculations.sh) emits asadm command output for calculation verification. |
| Workbook/source mapping | [docs/CALCULATION_CATALOG.md](docs/CALCULATION_CATALOG.md) | Cell refs and workbook sources live in catalog only; [Tool_Aerospike_Sizing_Estimator_(10_14).xlsx](Tool_Aerospike_Sizing_Estimator_(10_14).xlsx) in repo root when present. Do not embed cell refs in application code. |

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
- **Config:** Defaults and slider ranges live in [config/inputs.json](config/inputs.json); restart app after editing.
- **Calculations:** [docs/CALCULATIONS.md](docs/CALCULATIONS.md) is the source of truth; no cell references in code; [docs/CALCULATION_CATALOG.md](docs/CALCULATION_CATALOG.md) for workbook traceability.
- **Total memory used base** = Primary Index Shmem (64 B per replicated object) + Secondary Index Shmem (SI cushion 16 MiB in formulas.py).
- **Server instance specs** (vCPUs, RAM, Storage, Networking) are stored and exported; only RAM (available_memory_gb) is used in calculations.
- Collectinfo ingestion returns `cluster` + `namespaces` (and legacy flat). Load accepts .zip, .tgz, .tar. No-device namespaces get In-Memory (MMM), avg_record_size 0. Sample bundle: `bundles/fidelity-case00044090-20250226.zip` (when present).

---

## After a session

Update [docs/SESSION_LOG.md](docs/SESSION_LOG.md) with: date/session id, summary of work, files changed, and any decisions or follow-ups. This keeps context for the next agent or session.
