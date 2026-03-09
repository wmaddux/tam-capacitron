# Collectinfo input mapping

This document records how **CapacityInputs** are populated when loading from collectinfo. The ingestor runs **asadm** against a collectinfo bundle, parses the output, and the **mapping layer** converts that dict into `CapacityInputs` (direct fields, calculated fields, and defaults).

## Parameter classification: direct vs calculated

| Parameter | Source | asadm / parser | Notes |
|-----------|--------|----------------|-------|
| **replication_factor** | Direct | Namespace Summary → Replication Factors | 1:1. |
| **nodes_per_cluster** | Direct | Cluster Summary → Cluster Size | 1:1. |
| **devices_per_node** | Direct | Cluster Summary → Devices Per-Node | 1:1. |
| **device_size_gb** | Derived | (Device Total TB × 1024) / Devices Total | From Cluster or Namespace Summary. |
| **available_memory_gb** | Default | Not in summary | Default 64; document. |
| **overhead_pct** | Default | Not in asadm summary | Default 0.15. |
| **master_object_count** | Direct | Namespace Summary → Master/Objects (K/M/G parsed) | 1:1. |
| **avg_record_size_bytes** | Calculated | data_used_bytes / (master_object_count × replication_factor) | Device Used (TB) → bytes; mapping layer computes. |
| **read_pct** | From summary | Namespace Summary → Cache Read% | read_pct = value/100; write_pct = 1 - read_pct. |
| **write_pct** | Calculated | 1 - read_pct | |
| **tombstone_pct** | Default | Not in summary | Default 0. |
| **si_count** | Optional | show sindex / info sindex | Not from summary by default; mapping default. |
| **si_entries_per_object** | Default or stats | From sindex if added | Default 0. |
| **nodes_lost** | Not from bundle | — | Always 0 when loading from collectinfo. |

## asadm commands and flow

- **Primary:** `asadm -cf <bundle_path> -e "summary"`. Provides Cluster Summary (Cluster Size, Devices Total, Devices Per-Node, Device Total/Used) and Namespace Summary (Replication Factors, Cache Read%, Master objects, Device Total per namespace).
- **Parsing:** Pipe-delimited tables; "Cluster Summary" block then "Namespace Summary" block. K/M/G suffixes parsed (e.g. 6.447 G → 6.447e9). Device Total in TB → device_size_gb = (Device Total TB × 1024) / Devices Total.
- **Namespace choice:** One namespace per run. Use env **`CAPACITRON_NAMESPACE`** to choose; else first or largest by Master objects.
- **Dependency:** **asadm** must be on PATH. No SQLite or tam-flash-report. If asadm is missing or the command fails, the ingestor returns stub values.

## Ingestor output contract (target)

The mapping layer expects a **dict** from the ingestor with these keys (all optional; missing → mapping uses engine defaults):

| CapacityInput | Ingestor key(s) or formula |
|---------------|----------------------------|
| replication_factor | `replication_factor` |
| nodes_per_cluster | `nodes_per_cluster` |
| devices_per_node | `devices_per_node` |
| device_size_gb | `device_size_gb` |
| available_memory_gb | `available_memory_gb` (default 64) |
| overhead_pct | default 0.15 |
| master_object_count | `object_count` or `master_object_count` |
| avg_record_size_bytes | `data_used_bytes / (object_count * replication_factor)` in mapping |
| read_pct | `read_pct` (from Cache Read%) |
| write_pct | 1 - read_pct |
| tombstone_pct | default 0 |
| si_count | mapping default |
| si_entries_per_object | default 0 |
| nodes_lost | 0 |

## See also

- [PLAN.md](../PLAN.md) – Phase 3 scope, bundle handling.
- [core/model.py](../core/model.py) – `CapacityInputs` definition.
- [ingest/asadm_ingest.py](../ingest/asadm_ingest.py) – asadm runner and summary parser.
