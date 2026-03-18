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

### 2026-03-17 Load from collectinfo fixes; IOPS/Throughput defaults; UI cleanup and column layout

- **Summary:** (1) **Load from collectinfo:** Cluster name now populated from asadm Cluster Summary "Cluster Name" (ingest `_build_cluster_dict_from_summary` sets `cluster_name`; mapping and UI pass it through). IOPS per disk (K) and Throughput per disk (MB/s) are set to **fixed values** 320 and 1500 when loading from collectinfo (mapping layer defaults; not derived from bundle). (2) **Defaults:** IOPS per disk (K) and Throughput per disk (MB/s) now default to **320** and **1500** everywhere: `core/model.py` ClusterInputs, `config/inputs.json` cluster, `app/main.py` ClusterBody, and UI `defaultCluster()` and fallbacks. Throughput per disk slider **max** increased from 1000 to **3000** (UI and config). (3) **UI cleanup:** Moved IOPS and Throughput **above** Nodes lost and grouped them with Overhead % in a new **Overhead & performance** subsection (small heading); topology is now nodes, devices, device size only; order is topology → Overhead & performance → Resilience (Nodes lost, Data growth). (4) **Column layout:** First two columns fixed at **480px**, third column **flexible** (`minmax(0, 1fr)`); layout stacks to one column below 1100px (was 1000px). Assumption: at ~1440px viewport the first two columns stay fixed and the third adjusts.
- **Files changed/created:** `ingest/asadm_ingest.py` (cluster_name from Cluster Summary), `ingest/mapping.py` (iops_per_disk_k 320, throughput_per_disk_mbs 1500), `app/static/index.html` (defaultCluster 320/1500; Overhead & performance subsection; CLUSTER_KEYS_OVERHEAD_PERF; column grid 480px 480px 1fr; throughput max 3000; param-help array), `config/inputs.json` (cluster 320/1500; throughput slider max 3000), `core/model.py` (ClusterInputs defaults 320/1500), `app/main.py` (ClusterBody defaults 320/1500), `tests/test_asadm_ingest.py` (test_parse_summary_output_multi_cluster_name_from_summary), `tests/test_mapping.py` (assert iops/throughput in ingestor_multi test).
- **Decisions / notes:** Cluster name comes from summary only when "Cluster Name" line exists. Performance values are not derived from collectinfo; they are constants (320 K, 1500 MB/s) when loading from collectinfo and as initial/default values.
- **Follow-ups:** None required. Optional: Show my work for Data growth and Performance step-by-step; run full test suite with venv that has fastapi.

---

### 2026-03-17 Connect inputs to outputs; Growth and Performance sections

- **Summary:** Implemented plan: (1.1) Option C: kept Storage utilization % as-is, added **Storage utilization % with thresholds** using MaxDataPct (min of stop_writes_at_storage_pct, 100 − min_available_storage_pct across namespaces); documented FRAGMENTATION_FACTOR (0.024, cell C23). **Show my work:** Surface FRAGMENTATION_FACTOR, RECORD_METADATA_BYTES, SI constants (S, F, H) in Storage/Memory/Failure sections; added Storage utilization % with thresholds line when present. (1.2) Extended config/inputs.json with optional **cluster** and **namespaces**; get_default_cluster_and_namespaces() in app/config.py; GET /api/defaults and GET /api/input-config return { cluster, namespaces } when config has them; UI uses defaultsClusterAndNamespacesToState() for initial load and Load from defaults. (2.1) **Data growth:** cluster input Data growth (%/year) below Nodes lost; outputs projected_data_1yr_gb, headroom_to_stop_writes_pct, months_to_stop_writes_est; engine helpers and CALCULATIONS.md. (3) **Performance (Capacity planner v3.0):** cluster inputs IOPS per disk (K), Throughput per disk (MB/s); eight outputs (Total IOPS per Node, Estimated IOPS per cluster, Reads/Writes per second (k), Read/Write Bandwidth MB/s, Total Throughput per Node, Peak Throughput per cluster); effective read_pct/write_pct/avg_record_size weighted by data_stored_gb; formulas in core/formulas.py; CALCULATIONS.md and CALCULATION_CATALOG.md updated.
- **Files changed/created:** `core/formulas.py` (usable_storage_with_max_data_pct, storage_utilization_with_thresholds_pct; Performance functions), `core/engine.py` (MaxDataPct, storage with thresholds; data growth helpers; Performance aggregation), `core/model.py` (ClusterInputs: data_growth_pct_per_year, iops_per_disk_k, throughput_per_disk_mbs; CapacityOutputs: storage_utilization_with_thresholds_pct, usable_storage_with_thresholds_gb, growth outputs, Performance outputs), `app/config.py` (get_default_cluster_and_namespaces), `app/main.py` (ClusterBody new fields; api_defaults/api_input_config return cluster+namespaces when set), `config/inputs.json` (cluster, namespaces, sliders for new keys), `app/static/index.html` (Storage row with thresholds; Show my work constants; defaultsClusterAndNamespacesToState; Data growth input and outputs; Performance inputs and 8 outputs; PARAM_HELP/schema), `docs/CALCULATIONS.md` (FRAGMENTATION_FACTOR source; Storage with thresholds; Data growth; Performance), `docs/CALCULATION_CATALOG.md` (Performance table), `docs/PLAN_INPUTS_OUTPUTS_GROWTH_PERFORMANCE.md` (plan doc).
- **Decisions / notes:** Storage utilization % unchanged; second metric “with thresholds” uses same numerator, denominator = usable × (MaxDataPct/100). Data growth uses same usable_storage_with_thresholds_gb for headroom and months-to-stop-writes. Performance uses weighted-average read_pct, write_pct, avg_record_size by data_stored_gb across namespaces.
- **Follow-ups:** Optional: Show my work for Data growth and Performance step-by-step; run full test suite with venv that has fastapi.

---

### 2026-03-13 UI fine-tuning, config-driven defaults, Show my work, Server instance specs

- **Summary:** UI and meta updates so the next agent can resume from this point. **Calculations:** docs/CALCULATIONS.md is the source of truth; SI_CUSHION_PER_INDEX_PER_NODE_BYTES set to 16 MiB in doc and code. **UI:** Display values use thousand separators (fmt); OUTPUTS→Storage shows Data stored (TB) and removed redundant Total available storage (GB) row; subtle divider before Nodes lost. **Show my work:** Storage section clarifies usable vs raw denominator; added Memory utilization % and Failure scenario sections with same step-by-step style; CSS separation between sections. **Defaults:** Representative test cluster (6 nodes, 3 devices, 256 GB device, 128 GB RAM); then config-driven: config/inputs.json holds defaults and slider min/max/step; app/config.py loads it; GET /api/input-config returns both; frontend fetches on load; Pydantic and get_default_inputs() use config. **Server instance specs:** New Cluster sub-section (boxed like Capacity thresholds): vCPUs, RAM (GB) (replaces Available memory/node), Storage (text), Networking (text); vcpus/instance_storage/instance_networking in ClusterInputs and API (not used in calculations yet); divider before Nodes lost. **Docs:** README and config/README.md for customizing defaults/sliders; CALCULATIONS.md in docs list.
- **Files changed/created:** `docs/CALCULATIONS.md` (source of truth, SI 16 MiB, S/F/H explained), `core/formulas.py` (SI cushion 16 MiB), `core/model.py` (ClusterInputs vcpus/instance_storage/instance_networking; get_default_inputs from config), `app/config.py` (new), `config/inputs.json`, `config/README.md`, `app/main.py` (input-config, schema from config, ClusterBody new fields), `app/static/index.html` (fmt commas, Data stored TB, Show my work Memory/Failure/separators, Server instance specs box + divider, inputSchema from API), `docs/CALCULATION_CATALOG.md`, `docs/SESSION_LOG.md`, `MANIFEST.md`, `PLAN.md`, `README.md`.
- **Decisions / notes:** CALCULATION_SPREADSHEET.md removed earlier; CALCULATIONS.md is the single calculations reference. Config file is the single place to change defaults and slider ranges (restart app after edit). Server instance specs are for mapping cloud instance types; only RAM (available_memory_gb) affects calculations today.
- **Follow-ups:** Review each output value against CALCULATIONS.md and model docs (per-output calculation validation). Optional: automatic instance-type lookup for Server instance specs.

### 2026-03-13 Replace CALCULATION_SPREADSHEET with model-based calculations doc

- **Summary:** Removed docs/CALCULATION_SPREADSHEET.md and added docs/CALCULATIONS.md that lists capacity calculations by output and input situation, aligned with model_calculation_storage_util.md and model_calculation_mem_util.md. Updated MANIFEST.md and PROCESS_REDESIGN_UI_COMPUTE.md to reference the new doc.
- **Files changed/created:** `docs/CALCULATIONS.md` (new), `MANIFEST.md`, `docs/PROCESS_REDESIGN_UI_COMPUTE.md`, `docs/SESSION_LOG.md`. Deleted `docs/CALCULATION_SPREADSHEET.md`.
- **Decisions / notes:** Calculations doc describes formula flow and input situations (e.g. DATA M vs D for storage; PI/SI/DATA for memory; with/without tombstones) and where each step is implemented in core/formulas.py and core/engine.py. CALCULATION_CATALOG.md unchanged for workbook/cell traceability.
- **Follow-ups:** None.

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
- **Decisions / notes:** Total memory = Primary (RF×M×64) + SI (M×RF×E, S/F, N×H×K). Constants: SI_ENTRY_SIZE_BYTES=32, SI_FILL_FACTOR=0.75, SI_CUSHION_PER_INDEX_PER_NODE_BYTES=16 MiB. UI uses POST /api/compute-v2 and cluster + namespaces state; Load from collectinfo uses data.cluster and data.namespaces.
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
