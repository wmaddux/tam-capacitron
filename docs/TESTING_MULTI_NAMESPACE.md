# Testing multi-namespace (steps 1–3: contract + backend)

This document describes how to verify the multi-namespace contract, model, engine, and API (steps 1–3). It does not cover ingest or the UI.

## 1. Run the test suite

Install dependencies (including `httpx` for API tests): `pip install -r requirements.txt`. Then, from the repository root with the virtualenv activated:

```bash
source .venv/bin/activate
PYTHONPATH=. python -m pytest tests/ -v
```

**What to check:**

- **tests/test_engine.py**
  - `test_run_with_defaults` – legacy `run(CapacityInputs)` still works.
  - `test_run_with_workbook_like_inputs` – legacy run with workbook-like inputs.
  - `test_run_multi_one_namespace_matches_run` – **critical:** `run_multi(cluster, [one namespace])` produces the same outputs as `run(CapacityInputs)` for the same values. Confirms backward compatibility.
  - `test_run_multi_two_namespaces_aggregated` – two namespaces: `data_stored_gb` and `total_memory_used_base_gb` are the sum of the two single-namespace results; cluster-level fields (e.g. `device_total_storage_tb`) unchanged.
  - `test_run_multi_empty_namespaces_raises` – `run_multi(cluster, [])` raises `ValueError`.

- **tests/test_api_compute_v2.py**
  - `test_api_compute_legacy_returns_outputs` – `POST /api/compute` with flat body returns 200 and output fields.
  - `test_api_compute_v2_one_namespace_matches_legacy` – **critical:** same inputs sent as flat to `/api/compute` and as cluster + one namespace to `/api/compute-v2` yield the same outputs.
  - `test_api_compute_v2_two_namespaces_aggregated` – `/api/compute-v2` with two namespaces returns aggregated `data_stored_gb` and `total_memory_used_base_gb` (sum of the two single-namespace runs).
  - `test_api_compute_v2_empty_namespaces_400` – `/api/compute-v2` with `namespaces: []` returns 400.

All of the above should pass. If any fail, the backward-compatibility or aggregation behavior is broken.

## 2. Manual API check (optional)

Start the app:

```bash
PYTHONPATH=. uvicorn app.main:app --reload
```

**Legacy endpoint (unchanged behavior):**

```bash
curl -s -X POST http://127.0.0.1:8000/api/compute \
  -H "Content-Type: application/json" \
  -d '{"nodes_per_cluster":4,"devices_per_node":2,"device_size_gb":256,"available_memory_gb":64,"overhead_pct":0.15,"master_object_count":1000000,"avg_record_size_bytes":500,"replication_factor":2,"read_pct":0.5,"write_pct":0.5,"tombstone_pct":0,"si_count":0,"si_entries_per_object":0,"nodes_lost":0}' \
  | jq .
```

You should see `storage_utilization_pct`, `data_stored_gb`, `effective_nodes`, etc.

**Compute-v2 (one namespace, same result as legacy):**

```bash
curl -s -X POST http://127.0.0.1:8000/api/compute-v2 \
  -H "Content-Type: application/json" \
  -d '{
    "cluster": {"nodes_per_cluster":4,"devices_per_node":2,"device_size_gb":256,"available_memory_gb":64,"overhead_pct":0.15,"nodes_lost":0},
    "namespaces": [{"name":"default","replication_factor":2,"master_object_count":1000000,"avg_record_size_bytes":500,"read_pct":0.5,"write_pct":0.5,"tombstone_pct":0,"si_count":0,"si_entries_per_object":0}]
  }' \
  | jq .
```

Compare `data_stored_gb` and `storage_utilization_pct` with the legacy response; they should match.

**Compute-v2 (two namespaces):**

Add a second object to `namespaces` with different `master_object_count` or `avg_record_size_bytes`. The response `data_stored_gb` and `total_memory_used_base_gb` should be larger (sum of the two namespaces), and `storage_utilization_pct` and `memory_utilization_base_pct` should reflect the aggregated totals.

## 3. Existing UI (regression)

The current UI still calls `POST /api/compute` with the flat body. After steps 1–3:

1. Start the app and open http://127.0.0.1:8000 .
2. Change a few sliders and confirm outputs update immediately.
3. Click **Load from defaults** and confirm outputs refresh.
4. Click **Export** and confirm the downloaded JSON contains both inputs and outputs in the expected shape.

No change to UI behavior is expected; this is a regression check.

## Summary

| Check | How |
|-------|-----|
| Backward compatibility (engine) | `pytest tests/test_engine.py -v`; `test_run_multi_one_namespace_matches_run` must pass. |
| Backward compatibility (API) | `pytest tests/test_api_compute_v2.py -v`; `test_api_compute_v2_one_namespace_matches_legacy` must pass. |
| Aggregation (engine) | `test_run_multi_two_namespaces_aggregated` must pass. |
| Aggregation (API) | `test_api_compute_v2_two_namespaces_aggregated` must pass. |
| Empty namespaces rejected | `test_run_multi_empty_namespaces_raises` and `test_api_compute_v2_empty_namespaces_400` must pass. |
| Existing UI | Manual: sliders, Load from defaults, Export still work. |
