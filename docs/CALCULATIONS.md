# Capacity calculations

This document is the **source of truth** for capacity calculations. It lists calculations as defined in [model_calculation_storage_util.md](model_calculation_storage_util.md) and [model_calculation_mem_util.md](model_calculation_mem_util.md), and how they behave under different input combinations. Implementation lives in `core/formulas.py` and `core/engine.py`.

---

## Constants

The letters in parentheses **(S)**, **(F)**, **(H)** are the symbols used in the Secondary Index Shmem formula: data bytes per index ≈ Entries × **(S**/F), cushion = N × **H** × K. **S** = entry size (bytes), **F** = fill factor (0–1), **H** = cushion per index per node (bytes).

| Name | Value | Used in |
|------|-------|--------|
| BytesPerGB | 1024³ | Data bytes → GB; system memory budget |
| StorageOverheadPct / FRAGMENTATION_FACTOR | 0.024 | Usable device capacity (1 − this) × raw. Source: Capacity planner spreadsheet cell C23; defined in `core/formulas.py`. |
| RECORD_METADATA_BYTES | 64 | Primary Index Shmem: 64 bytes per replicated object |
| SI_ENTRY_SIZE_BYTES (S) | 32 | Secondary index entry size (bytes) |
| SI_FILL_FACTOR (F) | 0.75 | SI index fill factor (0–1) |
| SI_CUSHION_PER_INDEX_PER_NODE_BYTES (H) | 16 MiB | Fixed cushion per index per node (16 × 1024² bytes) |

---

## Storage utilization %

### Inputs that affect it

**Cluster:** NodesPerCluster, DevicesPerNode, DeviceSizeGB, StorageOverheadPct, StopWritesStoragePct, MinAvailStoragePct  

**Namespace:** StoragePattern_ns, ReplicationFactor_ns, MasterObjectCount_ns, AvgRecordSizeBytes_ns, CompressionSavingsPct_ns, TombstonePct_ns

### Input situations

The **third character (DATA)** of StoragePattern_ns is either `'M'` or `'D'`:

- **DATA = 'D':** This namespace’s data is on device. The namespace contributes **DeviceDataGB_ns = DataGB_ns** to the storage utilization numerator.
- **DATA = 'M':** Data is in memory only. **DeviceDataGB_ns = 0**; the namespace does not contribute to device storage utilization.

So only namespaces with data on device (e.g. HMA MMD, all-flash DDD) contribute to the numerator.

### Calculation steps (same order as model)

**1. Cluster usable device capacity**

- RawDeviceGB_cluster = NodesPerCluster × DevicesPerNode × DeviceSizeGB  
- MaxDataPct = min(StopWritesStoragePct, 100 − MinAvailStoragePct)  
- UsableDeviceGB_cluster = RawDeviceGB_cluster × (1 − StorageOverheadPct) × (MaxDataPct / 100)

**2. Per-namespace device data**

- LiveRecs_ns = MasterObjectCount_ns × ReplicationFactor_ns  
- TotalRecs_ns = LiveRecs_ns × (1 + TombstonePct_ns)  
- EffectiveRecordSizeBytes_ns = AvgRecordSizeBytes_ns × (1 − CompressionSavingsPct_ns)  
- DataBytes_ns = TotalRecs_ns × EffectiveRecordSizeBytes_ns  
- DataGB_ns = DataBytes_ns / BytesPerGB  

By placement:

- DataPlacement = third character of StoragePattern_ns  
- If DataPlacement == 'D': DeviceDataGB_ns = DataGB_ns  
- Else: DeviceDataGB_ns = 0  

Sum over namespaces: **TotalDeviceDataGB_all_ns** = sum over all ns of DeviceDataGB_ns

**3. Final**

- **StorageUtil_%** = (TotalDeviceDataGB_all_ns / UsableDeviceGB_cluster) × 100

### Implemented in

`core/formulas.py`: `total_usable_storage_cluster_gb` (denominator; app uses FRAGMENTATION_FACTOR for overhead), `storage_utilization_pct`. A second output **Storage utilization % with thresholds** uses denominator = total_usable_storage_gb × (MaxDataPct / 100) with MaxDataPct = min(stop_writes_at_storage_pct, 100 − min_available_storage_pct) (min across namespaces); see `usable_storage_with_max_data_pct`, `storage_utilization_with_thresholds_pct`.  
`core/engine.py`: Per-namespace data size and placement; aggregation of storage contribution (PI + SI + data on D); then `storage_utilization_pct(total_storage_used_gb, total_usable_storage_gb)`. Engine also computes `storage_utilization_with_thresholds_pct` and `usable_storage_with_thresholds_gb`. The model doc defines the numerator as data-on-device only; the engine uses placement-aware total storage used (PI/SI/data on D) for the numerator.

---

## Memory utilization %

### Inputs that affect it

**Cluster:** NodesPerCluster, MemoryTotalGB_per_node, StopWritesSysMemoryPct  

**Namespace:** StoragePattern_ns, IndexBytesWithTombs_ns, MemDataBytesWithTombs_ns, TombstonePct_ns

### Input situations

- **Placement (PI/SI/DATA = M or D):** Components in **M** count toward memory; components in **D** count toward storage (or zero for memory). So PI='M' → primary index shmem counts as memory; DATA='M' → in-memory data counts as memory; DATA='D' → no data memory for that namespace.
- **With vs without tombstones:** Index (and data) bytes can be expressed including tombstones or normalized to “no tombstones” by dividing by (1 + TombstonePct_ns).

### Calculation steps (same order as model)

**1. Effective system memory budget**

- SysMemBudgetBytes_cluster = NodesPerCluster × MemoryTotalGB_per_node × (StopWritesSysMemoryPct / 100) × BytesPerGB  

The app uses available memory after overhead (available_memory_gb × (1 − overhead_pct)) and does not currently apply StopWritesSysMemoryPct in the denominator; see model doc for the full definition.

**2. Per-namespace memory (with / without tombstones)**

- IndexBytesNoTombs_ns = IndexBytesWithTombs_ns / (1 + TombstonePct_ns)  
- MemDataBytesNoTombs_ns = MemDataBytesWithTombs_ns / (1 + TombstonePct_ns)  
- TotalMemBytesWithTombs_ns = IndexBytesWithTombs_ns + MemDataBytesWithTombs_ns  
- TotalMemBytesNoTombs_ns = IndexBytesNoTombs_ns + MemDataBytesNoTombs_ns  

Aggregate: TotalMemBytesWithTombs_all_ns, TotalMemBytesNoTombs_all_ns = sums over namespaces.

**3. Final**

- **MemoryUtil_with_tombstones_%** = (TotalMemBytesWithTombs_all_ns / SysMemBudgetBytes_cluster) × 100  
- **MemoryUtil_without_tombstones_%** = (TotalMemBytesNoTombs_all_ns / SysMemBudgetBytes_cluster) × 100  

The UI shows “Memory utilization (base) %” (without tombstones) and “Memory utilization (w/ tombstones) %”.

### Implemented in

`core/formulas.py`: `available_memory_after_overhead_gb`, `available_mem_per_cluster_gb`, `primary_index_shmem_gb`, `secondary_index_shmem_gb`, `total_memory_used_base_gb`, `memory_utilization_base_pct`.  
`core/engine.py`: Per-namespace placement (PI/SI/data in M vs D); tombstone factor applied to index memory; aggregation of memory used; memory utilization from aggregated totals.

---

## Cluster-only outputs (no namespace dimension)

Same for all runs; only cluster inputs matter.

| Output | Formula (business terms) | Implemented in |
|--------|--------------------------|-----------------|
| Device total storage (TB) | (Nodes × devices per node × device size GB) ÷ 1024 | `device_total_storage_tb` |
| Total device count | Nodes × devices per node | `total_device_count` |
| Available memory per cluster (GB) | Nodes × available memory after overhead per node | `available_memory_after_overhead_gb`, then `available_mem_per_cluster_gb` |
| Effective nodes (failure) | max(0, Nodes − nodes lost) | `effective_nodes` |
| Failure usable storage (GB) | Effective nodes × devices per node × device size × (1 − fragmentation factor) | `failure_usable_storage_gb` |

---

## Failure scenario

Same formulas as the healthy cluster, but the denominator uses **effective nodes** and **failure capacity**:

- **Failure storage utilization %** = 100 × (same numerator as healthy: total storage used or total device data) ÷ failure usable storage GB  
- **Failure memory utilization %** = 100 × (total memory used GB) ÷ (effective_nodes × available memory after overhead per node)

Implemented in: `failure_usable_storage_gb`, `failure_storage_utilization_pct`; engine uses same aggregated totals with failure denominators.

---

## Data growth

**Input:** Cluster-level **data_growth_pct_per_year** (annual growth rate, %).

**Outputs:**

- **Projected data (1 yr, GB)** = current data_stored_gb × (1 + data_growth_pct_per_year / 100).
- **Headroom to stop-writes %** = 100 × (usable_storage_with_thresholds_gb − data_stored_gb) / usable_storage_with_thresholds_gb. Uses the same threshold-based usable storage as “Storage utilization % with thresholds”. None when usable_storage_with_thresholds_gb ≤ 0.
- **Months to stop-writes (est)** = 12 × log(limit_gb / data_stored_gb) / log(1 + data_growth_pct_per_year/100) when growth > 0 and limit > current data; else None.

Implemented in: `core/engine.py` (`_projected_data_1yr_gb`, `_headroom_to_stop_writes_pct`, `_months_to_stop_writes_est`).

---

## Performance (Capacity planner v3.0)

**Source:** Copy of Capacity planner v3.0 - &lt;customer&gt; spreadsheet.

**Inputs:** Cluster: **IOPS per disk (K)**, **Throughput per disk (MB/s)**. Effective **Avg Read pct**, **Avg Write pct**, **Average record size (bytes)** from namespaces (weighted average by data_stored_gb).

**Outputs and formulas:**

| Output | Formula |
|--------|--------|
| Total IOPS per Node (K) | Devices per node × IOPS per disk (K) |
| Estimated IOPS (K) per cluster | Nodes per cluster × Total IOPS per Node (K) |
| Reads per second (k) | Avg Read pct × Estimated IOPS (K) per cluster |
| Writes per second (k) | Avg Write pct × Estimated IOPS (K) per cluster |
| Read Bandwidth (MB/s) | Reads per second (k) × 1000 × Avg record size (bytes) / 1024² |
| Write Bandwidth (MB/s) | Writes per second (k) × 1000 × Avg record size (bytes) / 1024² |
| Total Throughput per Node (MB/s) | Devices per node × Throughput per disk (MB/s) |
| Peak Throughput per cluster (MB/s) | Total Throughput per Node (MB/s) × Nodes per cluster |

Implemented in: `core/formulas.py` (performance functions), `core/engine.py` (effective read/write/record size; aggregation).

---

## Placement summary

For each component (Primary index, Secondary index, Data), placement is **M** (memory) or **D** (device):

| Component | M | D |
|-----------|---|---|
| Primary index (PI) | Contributes to **memory** (shmem) | Contributes to **storage** (same size on disk) |
| Secondary index (SI) | Contributes to **memory** (shmem) | Contributes to **storage** (same size on disk) |
| Data | Contributes to **memory** (record bodies in RAM) | Contributes to **storage** (data on device; compression_ratio applied) |

**Tombstones:** The tombstone factor (1 + TombstonePct_ns) applies only to **index memory** (PI + SI in M), not to data-in-memory. Collectinfo-derived shmem already includes tombstones; do not apply the factor again when using observed bytes from collectinfo.
