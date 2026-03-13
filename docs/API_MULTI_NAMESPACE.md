# Multi-namespace API contract

This document defines the request and response shape for multi-namespace capacity computation. Single-namespace is represented as one element in `namespaces`; there is no separate single-namespace format.

## Request shape (cluster + namespaces)

- **cluster** (object): cluster-level parameters (one value for the whole cluster).
  - **cluster_name** (string, optional): display label for the cluster (e.g. "prod"). Not used in calculations.
  - **nodes_per_cluster** (number)
  - **devices_per_node** (number)
  - **device_size_gb** (number)
  - **available_memory_gb** (number)
  - **overhead_pct** (number, 0–1)
  - **nodes_lost** (number)
  - **default_storage_pattern** (string, optional): default for new namespaces (e.g. `"HMA (MMD)"`). Used by load/export; engine uses per-namespace values.

- **namespaces** (array of objects): one object per namespace. Each object has workload parameters:
  - **name** (string): namespace identifier (e.g. "wi-pzn"). Used for display and export.
  - **replication_factor** (number)
  - **master_object_count** (number)
  - **avg_record_size_bytes** (number)
  - **read_pct** (number, 0–1)
  - **write_pct** (number, 0–1)
  - **tombstone_pct** (number, 0–1)
  - **si_count** (number)
  - **si_entries_per_object** (number)
  - **storage_pattern** (string, optional): e.g. `"HMA (MMD)"`, `"In-Memory (MMM)"`, `"All Flash (DDD)"`, `"DMD"`, `"Custom"`. Default `"HMA (MMD)"`.
  - **placement** (object, optional): `{ "primary": "M"|"D", "si": "M"|"D", "data": "M"|"D" }`. If omitted, derived from `storage_pattern` (HMA→MMD, In-Memory→MMM, All Flash→DDD, DMD→DMD).
  - **compression_ratio** (number, optional): 0–1, compressed/logical (1.0 = no compression). Default 1.0.
  - **stop_writes_at_storage_pct** (number, optional): 0–100, default 90. Passed through for future use.
  - **evict_at_memory_pct** (number, optional): 0–100, default 95. Passed through for future use.
  - **min_available_storage_pct** (number, optional): 0–20, default 5. Passed through for future use.

At least one namespace is required. The engine aggregates data stored, memory used, and storage used (by placement) across all namespaces and computes cluster-level utilization from those totals.

## Response shape (aggregated outputs)

Same as the existing capacity outputs: a single flat object with cluster-level metrics (storage utilization %, memory utilization %, failure scenario, etc.). These are computed from the **aggregated** data stored, memory used, and storage used across all namespaces (sum of per-namespace values; utilization = totals ÷ cluster available).

- **total_storage_used_gb** (number): Sum of per-namespace storage (PI + SI + data on D, with compression). Used for storage utilization.
- **per_namespace** (array of objects): Per-namespace breakdown. Each element has **name**, **data_stored_gb**, **memory_used_gb**, **storage_used_gb** (and optionally primary/SI breakdown) for breakdown UI or export.

## Endpoints

- **POST /api/compute** (existing): Accepts the legacy flat body (all inputs in one object). Backend maps to cluster + one namespace and returns the same aggregated output. Unchanged for backward compatibility.
- **POST /api/compute-v2**: Accepts `{ "cluster": { ... }, "namespaces": [ { ... }, ... ] }`. Returns aggregated outputs. Use this when the UI sends the cluster/namespaces structure.

## Backward compatibility

The existing flat `CapacityInputs` shape (replication_factor, nodes_per_cluster, ..., nodes_lost) is equivalent to: cluster = { nodes_per_cluster, devices_per_node, device_size_gb, available_memory_gb, overhead_pct, nodes_lost }, namespaces = [ { name: "", replication_factor, master_object_count, avg_record_size_bytes, read_pct, write_pct, tombstone_pct, si_count, si_entries_per_object } ]. The engine produces identical results for that case.
