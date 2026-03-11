# tam-capacitron

Dynamic Aerospike capacity planning tool: experiment with inputs (topology, workload, resilience) and see utilization and performance estimates in real time. Load inputs from manual entry, defaults, or a collectinfo bundle; export configurations for sharing.

**Scope:** Multi-namespace supported (cluster + namespaces; Add/Remove namespace in UI). Cluster has a default storage pattern; each namespace has storage pattern (HMA, In-Memory, All Flash, DMD, Custom), compression, and capacity thresholds. Column 3: **Parameter help** (click a parameter label) and **Show my work** (step-by-step storage utilization). **Stack:** Web UI (HTML/JS) + Python backend (FastAPI).

## Requirements

- **Python 3.10+** (for venv and dependencies)
- **asadm** on PATH (optional): required only for **Load from collectinfo** when using a zip bundle. If missing, that action uses stub values.

## Install

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the app

```bash
source .venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000** in a browser.

**Port in use?** Use another port: `uvicorn app.main:app --reload --port 8001`, or free 8000 (e.g. `lsof -i :8000` then `kill <PID>`).

## Using the app

- **Inputs:** Use sliders to change topology, memory, workload, and resilience; outputs update immediately.
- **Load from defaults:** Resets all inputs to safe minimums and refreshes outputs.
- **Load from collectinfo:** Upload a bundle (zip) or a collectinfo file; the button shows "Loading…" while the request runs. For zip bundles the app uses **asadm** to parse; asadm must be on PATH. Optional: set **`CAPACITRON_NAMESPACE`** to choose a namespace when the bundle has multiple. See [docs/COLLECTINFO_INPUT_MAPPING.md](docs/COLLECTINFO_INPUT_MAPPING.md).
- **Export:** Downloads a JSON file with all current inputs and outputs (standard output format) for storage or sharing.

## Run tests

To verify the installation and engine:

```bash
source .venv/bin/activate
PYTHONPATH=. python -m pytest tests/ -v
```

## Documentation

- [MANIFEST.md](MANIFEST.md) – **Start here for new agents:** repo map, key code, how to run, scope.
- [docs/SESSION_LOG.md](docs/SESSION_LOG.md) – Per-session work log.
- [docs/COLLECTINFO_INPUT_MAPPING.md](docs/COLLECTINFO_INPUT_MAPPING.md) – How Load from collectinfo maps bundle data to inputs.
- [docs/API_MULTI_NAMESPACE.md](docs/API_MULTI_NAMESPACE.md) – Multi-namespace API (POST /api/compute-v2).
- [docs/CALCULATION_CATALOG.md](docs/CALCULATION_CATALOG.md) – All calculations (Primary/SI memory, storage, utilization).
- [PLAN.md](PLAN.md) – Design, scope, and roadmap.

Contributors: see [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming and push workflow.
