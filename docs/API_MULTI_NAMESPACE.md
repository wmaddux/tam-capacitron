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

At least one namespace is required. The engine aggregates data stored and memory used across all namespaces and computes cluster-level utilization from those totals.

## Response shape (aggregated outputs)

Same as the existing capacity outputs: a single flat object with cluster-level metrics (storage utilization %, memory utilization %, failure scenario, etc.). These are computed from the **aggregated** data stored and memory used across all namespaces (sum of per-namespace data, sum of per-namespace memory; utilization = totals ÷ cluster available).

Optional future extension: include a **per_namespace** array with per-namespace data_stored_gb and memory_used_gb for breakdown UI or export.

## Endpoints

- **POST /api/compute** (existing): Accepts the legacy flat body (all inputs in one object). Backend maps to cluster + one namespace and returns the same aggregated output. Unchanged for backward compatibility.
- **POST /api/compute-v2**: Accepts `{ "cluster": { ... }, "namespaces": [ { ... }, ... ] }`. Returns aggregated outputs. Use this when the UI sends the cluster/namespaces structure.

## Backward compatibility

The existing flat `CapacityInputs` shape (replication_factor, nodes_per_cluster, ..., nodes_lost) is equivalent to: cluster = { nodes_per_cluster, devices_per_node, device_size_gb, available_memory_gb, overhead_pct, nodes_lost }, namespaces = [ { name: "", replication_factor, master_object_count, avg_record_size_bytes, read_pct, write_pct, tombstone_pct, si_count, si_entries_per_object } ]. The engine produces identical results for that case.
