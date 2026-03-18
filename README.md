# tam-capacitron

Dynamic Aerospike capacity planning tool: experiment with inputs (topology, workload, resilience) and see utilization and performance estimates in real time. Load inputs from manual entry, defaults, or a collectinfo bundle; export configurations for sharing.

When importing from collectinfo, only the inputs are affected. Downstream calculations are based on inputs (not direct results from CI). That way certain calculations can be compared and validated against actual CI results. 

**Scope:** Multi-namespace supported (cluster + namespaces; Add/Remove namespace in UI). Cluster has **Server instance specs** (vCPUs, RAM, Storage, Networking—for mapping cloud instance types; only RAM affects calculations), default storage pattern, topology, and resilience. Each namespace has storage pattern (HMA, In-Memory, All Flash, DMD, Custom), compression, and capacity thresholds. Defaults and slider ranges come from **config/inputs.json**. Column 3: **Parameter help** (click a parameter label) and **Show my work** (Storage, Memory, and Failure sections). **Stack:** Web UI (HTML/JS) + Python backend (FastAPI).

## Requirements

- **Python 3.10+** (for venv and dependencies)
- **asadm** on PATH (optional): required only for **Load from collectinfo** when using a zip bundle. If missing, that action uses stub values.

## Install

From the repository root. Use **Python 3.10 or newer** for the venv (required by the app).

```bash
python3.10 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

If `python3.10` isn’t on your PATH, install Python 3.10+ (e.g. [python.org](https://www.python.org/downloads/), Homebrew, or pyenv) and use that interpreter (e.g. `py -3.10 -m venv .venv` on Windows with the launcher).

## Run the app

```bash
source .venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000** in a browser.

**Port in use?** Use another port: `uvicorn app.main:app --reload --port 8001`, or free 8000 (e.g. `lsof -i :8000` then `kill <PID>`).

## Using the app

- **Inputs:** Use sliders and fields to change Cluster (Server instance specs, topology, Overhead & performance, Nodes lost, Data growth) and per-namespace workload; outputs update immediately. **IOPS per disk (K)** and **Throughput per disk (MB/s)** default to 320 and 1500; Throughput slider goes up to 3000 MB/s. Defaults and slider ranges are from [config/inputs.json](config/inputs.json). Layout: Inputs and Outputs columns are fixed width; the third column (Parameter help + Show my work) is flexible and stacks on narrow viewports.
- **Load from defaults:** Resets all inputs to config defaults and refreshes outputs.
- **Load from collectinfo:** Upload a bundle (**.zip**, **.tgz**, or **.tar**) or a collectinfo file; the button shows "Loading…" while the request runs. The app uses **asadm** to parse bundles; asadm must be on PATH. **Cluster name** is filled from the collectinfo Cluster Summary when present. **IOPS per disk (K)** and **Throughput per disk (MB/s)** are set to fixed defaults (320 and 1500) when loading from collectinfo. Namespaces with no device (e.g. in-memory-only) get storage pattern In-Memory (MMM) and contribute 0 to device storage; Device Total is parsed as TB or GB from the summary. Optional: set **`CAPACITRON_NAMESPACE`** to choose a namespace when the bundle has multiple. See [docs/COLLECTINFO_INPUT_MAPPING.md](docs/COLLECTINFO_INPUT_MAPPING.md).
- **Export:** Downloads a JSON file with all current inputs and outputs (standard output format) for storage or sharing.

**Customizing defaults and sliders:** Edit [config/inputs.json](config/inputs.json). The `defaults` object sets default values for all inputs; the `sliders` object sets `min`, `max`, and `step` for each UI slider. Restart the app after editing. See [config/README.md](config/README.md).

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
- [docs/CALCULATIONS.md](docs/CALCULATIONS.md) – Source of truth for capacity calculations (storage, memory, failure).
- [docs/CALCULATION_CATALOG.md](docs/CALCULATION_CATALOG.md) – Workbook/cell traceability for calculations.
- [config/README.md](config/README.md) – Customizing defaults and sliders.
- [PLAN.md](PLAN.md) – Design, scope, and roadmap.

Contributors: see [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming and push workflow.
