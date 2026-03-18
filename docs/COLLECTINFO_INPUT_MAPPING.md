# Collectinfo input mapping

This document records how **CapacityInputs** are populated when loading from collectinfo. The ingestor runs **asadm** against a collectinfo bundle, parses the output, and the **mapping layer** converts that dict into `CapacityInputs` (direct fields, calculated fields, and defaults).

## Parameter classification: direct vs calculated

| Parameter | Source | asadm / parser | Notes |
|-----------|--------|----------------|-------|
| **replication_factor** | Direct | Namespace Summary → Replication Factors | 1:1. |
| **cluster_name** | Direct | Cluster Summary → Cluster Name | Populated when present; UI shows it in Cluster card. |
| **nodes_per_cluster** | Direct | Cluster Summary → Cluster Size | 1:1. |
| **devices_per_node** | Direct | Cluster Summary → Devices Per-Node | 1:1. |
| **device_size_gb** | Derived | (Device Total × 1024 if TB, else as-is) / Devices Total | Cluster Summary "Device Total" may be TB or GB; parser is unit-aware. |
| **available_memory_gb** | From summary or derived | "Memory (Data + Indexes) Total" or "Memory Total" (TB/GB) / nodes; else 7.x: system_free_mem_kbytes / (system_free_mem_pct/100) per node, mean in GB | When summary has no Memory Total, ingest derives from `show statistics like system_free_mem -flip`. |
| **iops_per_disk_k** | Fixed when loading | Not from bundle | Mapping sets **320** (K) when loading from collectinfo. |
| **throughput_per_disk_mbs** | Fixed when loading | Not from bundle | Mapping sets **1500** (MB/s) when loading from collectinfo. |
| **overhead_pct** | Default | Not in asadm summary | Default 0.15. |
| **master_object_count** | Direct | Namespace Summary → Master/Objects (K/M/G parsed) | 1:1. |
| **avg_record_size_bytes** | Calculated | data_used_bytes / (master_object_count × replication_factor) | Per-namespace from show stat device_data_bytes/device_used_bytes. When master_object_count is 0 or namespace has no device (drives_total = 0), mapping sets 0 so the namespace contributes 0 to device storage. |
| **read_pct** | From summary | Namespace Summary → Cache Read% | read_pct = value/100; write_pct = 1 - read_pct. |
| **write_pct** | Calculated | 1 - read_pct | |
| **tombstone_pct** | Default | Not in summary | Default 0. |
| **si_count** | Optional | show sindex / info sindex | Not from summary by default; mapping default. |
| **si_entries_per_object** | Default or stats | From sindex if added | Default 0. |
| **nodes_lost** | Not from bundle | — | Always 0 when loading from collectinfo. |

## asadm commands and flow

- **Primary:** `asadm -cf <bundle_path> -e "summary"`. Provides Cluster Summary (Cluster Size, Devices Total, Devices Per-Node, Device Total/Used) and Namespace Summary (Replication Factors, Cache Read%, Master objects, Device Total per namespace).
- **Per-namespace Device Used (multi-namespace):** After parsing the summary, for each namespace we run `asadm -cf <bundle> -e "show stat namespace <NS> like device_data_bytes -flip"` (then `device_used_bytes` if needed). Sum the numeric column across nodes → **data_used_bytes** for that namespace. This aligns Data stored (GB) and Storage utilization % with asadm’s Device Used / Device Used% (see [model_calculation_storage_util.md](model_calculation_storage_util.md) and [test_collectinfo_derivations.sh](../tests/test_collectinfo_derivations.sh)).
- **Parsing:** Pipe-delimited tables; "Cluster Summary" block then "Namespace Summary" block. K/M/G suffixes parsed (e.g. 6.447 G → 6.447e9). Device Total: if the value contains "TB", treat as TB (× 1024 → GB); if "GB", use as GB. Each namespace row includes **drives_total** (Drives Total column); when 0, mapping sets **storage_pattern** = "In-Memory (MMM)" and **placement** data = M, and **avg_record_size_bytes** = 0. **object_count** is kept as-is (0 stays 0) so in-memory-only namespaces do not inflate device storage.
- **Namespace choice (single-namespace):** Use env **`CAPACITRON_NAMESPACE`** to choose; else first or largest by Master objects.
- **Bundles:** Load accepts .zip, .tgz, and .tar (asadm supports all three).
- **Dependency:** **asadm** must be on PATH. No SQLite or tam-flash-report. If asadm is missing or the command fails, the ingestor returns stub values.

## Ingestor output contract (target)

The mapping layer expects a **dict** from the ingestor with these keys (all optional; missing → mapping uses engine defaults):

| CapacityInput | Ingestor key(s) or formula |
|---------------|----------------------------|
| replication_factor | `replication_factor` |
| cluster_name | `cluster_name` (from Cluster Summary "Cluster Name") |
| nodes_per_cluster | `nodes_per_cluster` |
| devices_per_node | `devices_per_node` |
| device_size_gb | `device_size_gb` |
| available_memory_gb | `available_memory_gb` (from summary or derived from system_free_mem) |
| overhead_pct | default 0.15 |
| iops_per_disk_k | 320 (fixed when loading from collectinfo) |
| throughput_per_disk_mbs | 1500 (fixed when loading from collectinfo) |
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
