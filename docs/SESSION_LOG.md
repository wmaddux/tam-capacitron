# Session tracking

Log work done in each context session so the next agent or session can resume cleanly. **Update this file at the end of (or start of) each session** with a new entry below.

---

## Session entry template

Copy this block when adding a new session; fill and paste above the "---" under "Recent sessions."

```markdown
### YYYY-MM-DD [Short session title]

- **Summary:** One or two sentences on what was done.
- **Files changed/created:** List paths (e.g. `core/engine.py`, `docs/CALCULATION_CATALOG.md`).
- **Decisions / notes:** Any scope or design choices worth remembering.
- **Follow-ups:** What the next session might do (optional).
```

---

## Recent sessions

### 2026-03-12 Collectinfo load accuracy and derivation fixes

- **Summary:** Fixed Load from collectinfo so Data stored and Storage utilization % match asadm when loading multi-namespace bundles (e.g. nielsen). Device Total is parsed as TB or GB; namespaces with no device (Drives Total = 0) get object_count as-is (0 stays 0), avg_record_size 0, storage_pattern In-Memory (MMM), and placement data=M so they contribute 0 to device storage. Per-namespace device bytes from asadm device_data_bytes/device_used_bytes; mapping sets avg_record_size from data_used_bytes and uses drives_total to infer no-device namespaces. Derivation script updated: Device Total TB→GB, Memory (Data + Indexes) Total, device_used_bytes fallback for 6.x. UI no longer uses schema max for missing avg_record_size_bytes. Added scripts/gather_asadm_for_calculations.sh for uploading asadm outputs.
- **Files changed/created:** `ingest/asadm_ingest.py` (Device Total TB/GB, drives_total and object_count in namespace row, cluster Memory total parsing), `ingest/mapping.py` (avg_record_size 0 for no-device/zero objects, storage_pattern and placement from drives_total), `app/static/index.html` (load merge fallback for avg_record_size_bytes), `tests/test_collectinfo_derivations.sh` (Device Total unit, Memory total, device_used_bytes fallback), `scripts/gather_asadm_for_calculations.sh` (new), `tests/test_mapping.py` (no-device and drives_total tests), `README.md`, `MANIFEST.md`, `docs/SESSION_LOG.md`.
- **Decisions / notes:** Model docs (model_calculation_storage_util.md, model_calculation_mem_util.md) are the source for calculation logic. Calculation spreadsheet (CALCULATION_SPREADSHEET.md) is not the driver; plan was to fix calculations from model docs.
- **Follow-ups:** Optional: align storage utilization denominator with MaxDataPct (StopWritesStoragePct, MinAvailStoragePct) per model; derive StoragePattern from asadm config (index-type, sindex-type, storage-engine) when not using summary.

### 2026-03-10 Mockup and SESSION_LOG date corrections

- **Summary:** Created docs/mockups/mockup-capacity-combined.html as a static reference mockup derived from app/static/index.html (layout, Cluster default pattern, Namespace pattern pills/compression/thresholds, Outputs with breakdown and Data growth/Performance, Parameter help + Show my work). Corrected all SESSION_LOG.md entry dates from 2025-02-27 to 2026-02-27 for older sessions and 2026-03-10 for the Mockup UI restore session.
- **Files changed/created:** `docs/mockups/mockup-capacity-combined.html` (new), `docs/SESSION_LOG.md` (date updates + this entry).
- **Decisions / notes:** Mockup is for project context so agents have a standalone HTML reference; live app remains app/static/index.html.
- **Follow-ups:** None.

### 2026-03-10 Mockup UI restore, xlsx removal, docs for resume

- **Summary:** Restored full mockup UI to app/static/index.html after work was lost during a git history rewrite (stash lost). Re-implemented: combined mockup layout (cluster default storage pattern; per-namespace storage pattern pills, Custom placement, compression, capacity thresholds); column 3 Parameter help + Show my work panel with storage utilization step-by-step; "By pattern" breakdown in outputs; Data growth and Performance output cards; Load from collectinfo "Loading…" button state. Removed Capacity_planner_v3.0-fidelity_workbench.xlsx from repo and full git history (filter-branch). Updated MANIFEST.md, README.md, and SESSION_LOG.md so another agent can resume.
- **Files changed/created:** `app/static/index.html` (restored mockup UI, Show my work, Loading indicator, namespace pattern/compression/thresholds), `MANIFEST.md` (current scope, UI reference, workbook row), `README.md` (scope and Load from collectinfo note), `docs/SESSION_LOG.md` (this entry). Git history: xlsx file removed from all commits.
- **Decisions / notes:** UI state includes default_storage_pattern, and per-namespace storage_pattern, placement, compression, stop_writes_at_storage_pct, evict_at_memory_pct, min_available_storage_pct; export/load merge these. Engine and API request body unchanged (new fields optional). Show my work uses STORAGE_OVERHEAD_PCT = 0.024 (matches formulas.py fragmentation factor). When adding a namespace, defaultNamespace(state.cluster.default_storage_pattern) is used.
- **Follow-ups:** Optional: add optional API fields for new UI inputs when engine supports them; wire Data growth/Performance when backend provides data; add more "Show my work" sections (e.g. memory utilization).

### 2026-02-27 Phase 2 UI, memory formulas, docs, push

- **Summary:** Implemented Phase 2 UI with multi-namespace (three-column layout: Inputs | Outputs | Definition; Cluster card + Namespaces cards with Add/Remove; compute-v2, Load from defaults/collectinfo, Export). Fixed Total memory used base (GB) to equal Primary Index Shmem (64 bytes per replicated object) + Secondary Index Shmem (collectinfo-style: entries = M×RF×E, data + cushion). Set device size default/min to 50 GB. Updated MANIFEST, SESSION_LOG, README, and PLAN for new-agent onboarding; pushed to GitHub.
- **Files changed/created:** `app/static/index.html` (Phase 2 UI), `core/formulas.py` (primary_index_shmem_gb, secondary_index_shmem_gb, total_memory_used_base_gb), `core/engine.py` (wire new memory calc), `docs/CALCULATION_CATALOG.md` (Primary/SI/Total memory), `core/model.py` and `app/main.py` (device_size_gb 50), `MANIFEST.md`, `README.md`, `PLAN.md` (scope/state), `docs/SESSION_LOG.md`.
- **Decisions / notes:** Total memory = Primary (RF×M×64) + SI (M×RF×E, S/F, N×H×K). Constants: SI_ENTRY_SIZE_BYTES=32, SI_FILL_FACTOR=0.75, SI_CUSHION_PER_INDEX_PER_NODE_BYTES≈40 MiB. UI uses POST /api/compute-v2 and cluster + namespaces state; Load from collectinfo uses data.cluster and data.namespaces.
- **Follow-ups:** Optional: expose Primary/SI breakdown in UI or export; tune SI constants from real collectinfo if needed.

### 2026-02-27 Scope, manifest, session log

- **Summary:** Documented current scope (one namespace, one cluster; future multi-namespace). Created MANIFEST.md for new-agent onboarding and docs/SESSION_LOG.md for per-session work tracking.
- **Files changed/created:** `PLAN.md` (Scope section), `MANIFEST.md`, `docs/SESSION_LOG.md`.
- **Decisions / notes:** Scope lives in PLAN.md; manifest points to PLAN, catalog, strawman, session log, and CONTRIBUTING. Session log uses a template; each session should append an entry.
- **Follow-ups:** Update SESSION_LOG.md at end of each context session with work done.

### 2026-02-27 Sizing Estimator catalog and formula cleanup

- **Summary:** Removed all spreadsheet cell references from `core/formulas.py` and `core/model.py`. Added full Tool_Aerospike_Sizing_Estimator (Workload, AWS, Custom, Miscellaneous) parameters and calculations to docs/CALCULATION_CATALOG.md for future phases.
- **Files changed/created:** `core/formulas.py`, `core/model.py`, `docs/CALCULATION_CATALOG.md`.
- **Decisions / notes:** Cell refs exist only in CALCULATION_CATALOG.md for mapping; application code uses business-language only.

### 2026-02-27 Phase 0, 1, 2 execution

- **Summary:** Executed Phase 0 (README, CONTRIBUTING, .gitignore), Phase 1 (strawman UI/flow, core model, formulas, engine, tests), Phase 2 (FastAPI app, single-page UI with sliders, Load from defaults, Export to JSON, immediate reactivity).
- **Files changed/created:** `README.md`, `CONTRIBUTING.md`, `.gitignore`, `docs/STRAWMAN_UI_AND_FLOW.md`, `core/model.py`, `core/formulas.py`, `core/engine.py`, `core/__init__.py`, `tests/test_engine.py`, `tests/__init__.py`, `requirements.txt`, `app/main.py`, `app/__init__.py`, `app/static/index.html`.
- **Decisions / notes:** Run with `PYTHONPATH=. uvicorn app.main:app --reload`. First push to GitHub recommended after Phase 0–2.

### 2026-02-27 Plan creation and iterations

- **Summary:** Created and refined PLAN.md (design plan): architecture, UX, Phase 0–5, collectinfo via tam-flash-report, bundle parsing, comparison mode as saved states, Load buttons by source, strawman-before-calc, modular design, Option A web app + Python backend, formulas human-readable, immediate reactivity. Plan saved to project root as PLAN.md.
- **Files changed/created:** `PLAN.md` (and earlier Cursor plan file).
- **Decisions / notes:** Collectinfo is an input source (button), not a separate mode. Comparison = saved state vs saved state. Sample bundle: bundles/fidelity-case00044090-20250226.zip.
