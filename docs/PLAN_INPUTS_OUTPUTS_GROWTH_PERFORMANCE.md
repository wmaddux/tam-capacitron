# Plan: Connect inputs to outputs and finish Growth / Performance

This document is the working plan for the next phase. It extends the high-level [PLAN.md](../PLAN.md) and aligns with [MANIFEST.md](../MANIFEST.md) and [SESSION_LOG.md](SESSION_LOG.md).

---

## 1.1 Thresholds and FRAGMENTATION_FACTOR

**Where FRAGMENTATION_FACTOR comes from:** Defined in [core/formulas.py](../core/formulas.py) (line 13) as `0.024` — “(1 - this) = usable storage fraction”. Maps to Capacity planner spreadsheet **cell C23** ([docs/CALCULATION_CATALOG.md](CALCULATION_CATALOG.md)).

**Option C:** Keep existing **Storage utilization %** unchanged. Add new output **Storage utilization % with thresholds** (denominator = usable storage × MaxDataPct/100; MaxDataPct = min(stop_writes_at_storage_pct, 100 − min_available_storage_pct)).

---

## 1.2 Config defaults – full cluster + namespaces

Extend [config/inputs.json](../config/inputs.json) with optional `cluster` and `namespaces` so GET /api/input-config and get_default_inputs() return full cluster + namespaces. “Load from defaults” and initial page load both use this shape. See plan details for cluster/namespace key list.

---

## 2.1 Data growth – % per year, below Nodes lost

Cluster-level input **Data growth (%/year)** below “Nodes lost (failure)”. Outputs: Projected data (1 yr, GB), Headroom to stop-writes %, Months to stop-writes (est). Formulas and engine changes as in plan.

---

## 3. Performance – Capacity planner v3.0

New cluster inputs: **IOPS per disk (K)**, **Throughput per disk (MB/s)**. Outputs: Total IOPS per Node (K), Estimated IOPS (K) per cluster, Reads per second (k), Writes per second (k), Read/Write Bandwidth (MB/s), Total Throughput per Node (MB/s), Peak Throughput per cluster (MB/s). Formulas from “Copy of Capacity planner v3.0 - &lt;customer&gt;” spreadsheet. Use existing read_pct / write_pct; SI constants remain fixed.

---

## Show my work – surface fixed constants

**FRAGMENTATION_FACTOR** (and other fixed inputs) must appear by name and value in **Show my work** wherever they are used.

**Storage section:**

- Name the overhead explicitly: e.g. “**Storage overhead (FRAGMENTATION_FACTOR)** = 0.024 (2.4%)” and show it in the Usable storage line: “Usable storage = Device total × (1 − FRAGMENTATION_FACTOR) = …”.
- When **Storage utilization % with thresholds** is added, add a line showing **MaxDataPct** and the threshold inputs (stop_writes_at_storage_pct, min_available_storage_pct) used.

**Memory section:**

- **Primary Index:** Show **RECORD_METADATA_BYTES = 64** (bytes per replicated object) in the step that explains Primary Index Shmem (e.g. “Primary Index Shmem = RF × Master object count × 64 bytes / 1024³”).
- **Secondary Index:** Show the fixed constants where the SI formula is explained: **SI_ENTRY_SIZE_BYTES (S)** = 32, **SI_FILL_FACTOR (F)** = 0.75, **SI_CUSHION_PER_INDEX_PER_NODE_BYTES (H)** = 16 MiB (or 16,777,216 bytes), so the “Show my work” text matches [docs/CALCULATIONS.md](CALCULATIONS.md) and [core/formulas.py](../core/formulas.py).

**Failure section:**

- Failure usable storage uses the same fragmentation factor; add a brief note or reuse the same constant name so it’s clear the same 0.024 is applied.

**Performance section (when added):**

- Where Performance formulas are shown, list any fixed values used (e.g. if IOPS/throughput formulas use constants, show them).

**Implementation:** Update `buildShowMyWork()` in [app/static/index.html](../app/static/index.html) to inject these constant names and values (either hardcoded in the template to match formulas.py, or optionally from a small “constants” object in the front end that mirrors the backend). No backend API change required unless we later expose constants via API.

---

## Suggested order of work

1. 1.1 – Option C (new Storage utilization % with thresholds); document FRAGMENTATION_FACTOR.
2. **Show my work** – Add FRAGMENTATION_FACTOR and other fixed constants to Storage, Memory, and Failure sections as above.
3. 1.2 – Config and API for full cluster + namespaces.
4. 2.1 – Data growth input and outputs.
5. 3 – Performance inputs, formulas, and outputs; add Performance to Show my work if step-by-step is desired.

---

## Files to touch (summary)

| Area | Files |
|------|--------|
| 1.1 + Show my work (constants) | [core/formulas.py](../core/formulas.py), [core/engine.py](../core/engine.py), [core/model.py](../core/model.py), [app/static/index.html](../app/static/index.html), [docs/CALCULATIONS.md](CALCULATIONS.md) |
| 1.2 | [config/inputs.json](../config/inputs.json), [app/config.py](../app/config.py), [core/model.py](../core/model.py), [app/main.py](../app/main.py), [app/static/index.html](../app/static/index.html) |
| 2.1 | [core/model.py](../core/model.py), [core/engine.py](../core/engine.py), [app/main.py](../app/main.py), [app/static/index.html](../app/static/index.html), [docs/CALCULATIONS.md](CALCULATIONS.md) |
| 3 | [core/formulas.py](../core/formulas.py), [core/engine.py](../core/engine.py), [core/model.py](../core/model.py), [app/main.py](../app/main.py), [app/static/index.html](../app/static/index.html), [docs/CALCULATIONS.md](CALCULATIONS.md), [docs/CALCULATION_CATALOG.md](CALCULATION_CATALOG.md) |
