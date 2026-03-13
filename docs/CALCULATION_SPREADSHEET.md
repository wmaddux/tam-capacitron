# Calculation spreadsheet (comprehensive)

**Structure:** The listing **starts with outputs**. For each output we show **all calculations required** to achieve it, grouped by category. Multiple formulae may apply for a single output depending on inputs (e.g. **Aerospike version**, **Storage pattern / placement**, or other factors). No code changes until this spreadsheet is correct and validated.

**Group categories used:**
- **Constants** — Fixed values used in the formulas below.
- **Cluster-level** — Calculations that depend only on cluster inputs (no per-namespace workload).
- **Per-namespace** — Calculations done once per namespace from that namespace’s workload inputs.
- **By placement (storage pattern)** — Which components (Primary Index, Secondary Index, Data) count toward memory vs storage, depending on M/D placement.
- **By Aerospike version** — Formula or applicability differs by version (e.g. in-memory compression in 7.0+).
- **Namespace summarization** — How per-namespace values are combined into cluster-level totals and the final output.

Legacy cell refs and workbook sources: [CALCULATION_CATALOG.md](CALCULATION_CATALOG.md).

---

## Output: Storage utilization %

**Definition:** Percentage of cluster **usable device capacity** that is used by **namespace data on device** (DATA='D'). PI and SI on disk do **not** contribute to this numerator in the canonical model ([model_calculation_storage_util.md](model_calculation_storage_util.md)).

**Final formula:**  
**Storage utilization %** = 100 × ( **Total device data (GB)** ÷ **Usable device capacity (GB)** )

---

### Constants used for this output

| Constant | Value / source | Used in |
|----------|----------------|--------|
| BytesPerGB | 1024³ | DataBytes_ns → DataGB_ns |
| Cluster Storage Overhead Pct (StorageOverheadPct) | e.g. 0.024 (calc:Manual C23); manual if not from collectinfo | Usable device capacity |

*PI/SI constants are not used for this output (only data on device counts).*

---

### Cluster-level (no namespace)

| Calculation | Formula (business terms) | Feeds into |
|-------------|---------------------------|------------|
| Raw device capacity (GB) | Nodes × DevicesPerNode × DeviceSizeGB | Usable device capacity |
| MaxDataPct | min(StopWritesStoragePct, 100 − MinAvailStoragePct) | Usable device capacity (cap on usable fraction) |
| Usable device capacity (GB) | RawDeviceGB × (1 − StorageOverheadPct) × (MaxDataPct / 100) | Storage utilization % — **denominator** |

**Inputs used:** NodesPerCluster, DevicesPerNode, DeviceSizeGB, StorageOverheadPct, StopWritesStoragePct, MinAvailStoragePct

---

### Per-namespace (workload)

| Calculation | Formula (business terms) | Feeds into |
|-------------|---------------------------|------------|
| LiveRecs_ns | MasterObjectCount_ns × ReplicationFactor_ns | TotalRecs_ns |
| TotalRecs_ns | LiveRecs_ns × (1 + TombstonePct_ns) | DataBytes_ns |
| EffectiveRecordSizeBytes_ns | AvgRecordSizeBytes_ns × (1 − CompressionSavingsPct_ns) | DataBytes_ns |
| DataBytes_ns | TotalRecs_ns × EffectiveRecordSizeBytes_ns | DataGB_ns |
| DataGB_ns | DataBytes_ns / BytesPerGB | DeviceDataGB_ns (when DATA='D') |

**Inputs used (per namespace):** MasterObjectCount_ns, ReplicationFactor_ns, TombstonePct_ns, AvgRecordSizeBytes_ns, CompressionSavingsPct_ns

---

### By placement (storage pattern)

Only the **third character (DATA)** of StoragePattern_ns determines whether this namespace contributes to storage utilization.

| Condition | DeviceDataGB_ns |
|-----------|-----------------|
| 3rd char of StoragePattern_ns == 'D' | DeviceDataGB_ns = DataGB_ns |
| 3rd char == 'M' | DeviceDataGB_ns = 0 |

**Inputs used (per namespace):** StoragePattern_ns (3-char PI/SI/DATA)

---

### Namespace summarization

| Calculation | Formula (business terms) | Feeds into |
|-------------|---------------------------|------------|
| Total device data (GB) | Sum over all namespaces of DeviceDataGB_ns | Storage utilization % — **numerator** |
| Storage utilization (%) | 100 × (Total device data (GB) ÷ Usable device capacity (GB)) | — *(this is the output)* |

---

### Calculation order summary (Storage utilization %)

1. **Cluster-level:** Raw device capacity; MaxDataPct from StopWrites and MinAvail; Usable device capacity = Raw × (1 − StorageOverheadPct) × (MaxDataPct/100).
2. **Per namespace:** LiveRecs, TotalRecs (with TombstonePct), EffectiveRecordSize (with CompressionSavingsPct), DataBytes, DataGB.
3. **By placement:** If DATA='D' then DeviceDataGB_ns = DataGB_ns else 0.
4. **Summarization:** Total device data = sum(DeviceDataGB_ns); Storage utilization % = 100 × (Total device data ÷ Usable device capacity).

---

## Output: Memory utilization %

**Definition:** Percentage of **system memory budget** (cluster) used by index + data in memory. Canonical formulas in [model_calculation_mem_util.md](model_calculation_mem_util.md). Two variants: **with tombstones** and **without tombstones**.

**Final formulas:**  
- **Memory utilization with tombstones %** = 100 × (TotalMemBytesWithTombs_all_ns ÷ SysMemBudgetBytes_cluster)  
- **Memory utilization without tombstones %** = 100 × (TotalMemBytesNoTombs_all_ns ÷ SysMemBudgetBytes_cluster)

---

### Constants used for this output

| Constant | Value / source | Used in |
|----------|----------------|--------|
| BytesPerGB | 1024³ | SysMemBudgetBytes_cluster |

---

### Cluster-level (no namespace)

| Calculation | Formula (business terms) | Feeds into |
|-------------|---------------------------|------------|
| SysMemBudgetBytes_cluster | NodesPerCluster × MemoryTotalGB_per_node × (StopWritesSysMemoryPct / 100) × BytesPerGB | Memory utilization % — **denominator** |

**Inputs used:** NodesPerCluster, MemoryTotalGB_per_node, StopWritesSysMemoryPct

---

### Per-namespace (two modes)

**Mode A — From collectinfo:** Use observed bytes directly (already include tombstones).

| Input / calculation | Description | Feeds into |
|---------------------|-------------|------------|
| IndexBytesWithTombs_ns | index_used_bytes + sindex_used_bytes + set_index_used_bytes (sum across nodes) | TotalMemBytesWithTombs_ns |
| MemDataBytesWithTombs_ns | memory_data_bytes or data_used_bytes when DATA='M'; 0 when DATA='D' (sum across nodes) | TotalMemBytesWithTombs_ns |
| TotalMemBytesWithTombs_ns | IndexBytesWithTombs_ns + MemDataBytesWithTombs_ns | Aggregate; and NoTombs = WithTombs/(1+TombstonePct) per component |

**Mode B — From manual/planning:** Compute index (PI+SI) and data size from workload params; then apply tombstone factor to index only.

| Calculation | Formula (business terms) | Feeds into |
|-------------|---------------------------|------------|
| Index (PI+SI) from model | Primary Index Shmem + Secondary Index Shmem (from RF, M, SI count, SI entries, etc.) | IndexBytesNoTombs_ns (live only) |
| IndexBytesWithTombs_ns | IndexBytesNoTombs_ns × (1 + TombstonePct_ns) | TotalMemBytesWithTombs_ns |
| MemDataBytesWithTombs_ns | If DATA='M': MasterObjectCount×RF×AvgRecordSize (or with compression for 7.0+); if DATA='D': 0 | TotalMemBytesWithTombs_ns |

---

### By placement (storage pattern)

For memory, **DATA (3rd char)** determines whether record bodies count: DATA='M' → data in memory counts; DATA='D' → data on device, so MemDataBytes = 0 for this namespace.

---

### Per-namespace (without tombstones)

| Calculation | Formula (business terms) | Feeds into |
|-------------|---------------------------|------------|
| IndexBytesNoTombs_ns | IndexBytesWithTombs_ns / (1 + TombstonePct_ns) | TotalMemBytesNoTombs_ns |
| MemDataBytesNoTombs_ns | MemDataBytesWithTombs_ns / (1 + TombstonePct_ns) | TotalMemBytesNoTombs_ns |
| TotalMemBytesNoTombs_ns | IndexBytesNoTombs_ns + MemDataBytesNoTombs_ns | Memory util without tombstones % |

**Inputs used (per namespace):** TombstonePct_ns

---

### Namespace summarization

| Calculation | Formula (business terms) | Feeds into |
|-------------|---------------------------|------------|
| TotalMemBytesWithTombs_all_ns | Sum over namespaces of TotalMemBytesWithTombs_ns | Memory util with tombstones % |
| TotalMemBytesNoTombs_all_ns | Sum over namespaces of TotalMemBytesNoTombs_ns | Memory util without tombstones % |
| Memory util with tombstones (%) | 100 × (TotalMemBytesWithTombs_all_ns ÷ SysMemBudgetBytes_cluster) | — *(output)* |
| Memory util without tombstones (%) | 100 × (TotalMemBytesNoTombs_all_ns ÷ SysMemBudgetBytes_cluster) | — *(output)* |

---

### Calculation order summary (Memory utilization %)

1. **Cluster-level:** SysMemBudgetBytes_cluster from Nodes, MemoryTotalGB_per_node, StopWritesSysMemoryPct.
2. **Per namespace:** Either use IndexBytesWithTombs_ns and MemDataBytesWithTombs_ns (collectinfo) or compute from workload + StoragePattern; TotalMemBytesWithTombs_ns = Index + MemData.
3. **Without tombstones:** IndexBytesNoTombs = IndexWithTombs/(1+TombstonePct); MemDataNoTombs = MemDataWithTombs/(1+TombstonePct); TotalNoTombs = sum.
4. **Summarization:** Sum WithTombs and NoTombs across namespaces; divide each by SysMemBudgetBytes_cluster × 100.

---

*(Failure storage/memory utilization and other outputs can be added in the same output-first format. Process and input/output contract: [PROCESS_REDESIGN_UI_COMPUTE.md](PROCESS_REDESIGN_UI_COMPUTE.md).)*

---

## Reference: Constants (full list)

Below: full constants table for all outputs. Source sheet **calc:Manual**. Updates per calculations_verification_2.

| Calculation | Formula (business terms) | Applies when / Group | Application function | Notes |
|-------------|---------------------------|----------------------|----------------------|--------|
| Throughput per Disk | (value from source) | Always | `MTU_BYTES` or rename | **calc:Manual**:C21. Previously labeled MTU (bytes) 1500; verification doc: this constant is "Throughput per Disk". |
| IOPS per Disk | (value from source) | Always | `HEADER_OVERHEAD` or rename | **calc:Manual**:C22. Previously labeled Header overhead (bytes) 320; verification doc: this constant is "IOPS per Disk". |
| Cluster Storage Overhead Pct | 0.024 | Always; (1 − this) = usable storage fraction | `FRAGMENTATION_FACTOR` | **calc:Manual**:C23. Verification doc: this is "Cluster Storage Overhead Pct" (fragmentation factor). |
| Record metadata (bytes per replicated object) | 64 | Always; Primary Index Shmem | `RECORD_METADATA_BYTES` | 64 B per replicated object |
| SI entry size (bytes) | 32 | Always | `SI_ENTRY_SIZE_BYTES` | Collectinfo-style; S = average entry size (bytes). |
| SI fill factor | 0.75 | Always | `SI_FILL_FACTOR` | **F** = fill factor (0–1) for the SI index in formula Entries×(S/F). |
| SI cushion per index per node (bytes) | 16,777,216 (16 MiB) | Always | `SI_CUSHION_PER_INDEX_PER_NODE_BYTES` | **H**. Verification doc: should be **16** instead of 40 (i.e. 16 MiB = 16×1024² bytes, not 40 MiB). |

---

## 2. Cluster-level only (no namespace dimension)

These depend only on cluster inputs; no per-namespace workload. Same formula regardless of version or placement.

| Calculation | Formula (business terms) | Applies when / Group | Application function | Notes |
|-------------|---------------------------|----------------------|----------------------|--------|
| Device total storage (TB) | (Nodes × devices per node × device size GB) ÷ 1024 | Always | `device_total_storage_tb` | C9 |
| Total device count | Nodes × devices per node | Always | `total_device_count` | C10 |
| Available memory after overhead (GB per node) | Available memory per node × (1 − overhead pct) | Always | `available_memory_after_overhead_gb` | C18 |
| Memory overhead (GB) | Available memory − available after overhead | Always | `memory_overhead_gb` | C19 |
| Available memory per cluster (GB) | Nodes × available memory after overhead per node | Always | `available_mem_per_cluster_gb` | C59 |
| Usable storage per node (GB) | Devices per node × device size GB × (1 − fragmentation factor) | Always | `usable_storage_per_node_gb` | C55 term |
| Total usable storage cluster (GB) | Nodes × devices per node × device size GB × (1 − fragmentation factor) | Always | `total_usable_storage_cluster_gb` | C55 |
| Effective nodes (failure) | max(0, Nodes − nodes lost) | Failure scenario | `effective_nodes` | C70 |
| Failure usable storage (GB) | Effective nodes × devices per node × device size GB × (1 − fragmentation factor) | Failure scenario | `failure_usable_storage_gb` | C71 |

---

## 3. Per-namespace (workload-dependent)

Computed once per namespace from that namespace’s workload inputs. **Summarization** (next section) then aggregates over namespaces.

| Calculation | Formula (business terms) | Applies when / Group | Application function | Notes |
|-------------|---------------------------|----------------------|----------------------|--------|
| Total objects (replicated) | Replication factor × master object count | Per namespace | `total_objects` | C36 |
| Data size (GB) | (Master objects × replication × avg record size bytes) ÷ 1024³ | Per namespace; logical size before compression | `data_size_gb` | C54 |
| Primary Index Shmem (GB) | (RF × master object count × 64 bytes) ÷ 1024³ | Per namespace | `primary_index_shmem_gb` | PI in RAM |
| Secondary Index Shmem (GB) | Entries = M×RF×E; Data per index = Entries×(S/F); Cushion = N×H×K; Total SI = Data + Cushion; ÷ 1024³ | Per namespace; zero if si_count or si_entries_per_object = 0 | `secondary_index_shmem_gb` | Collectinfo-style |
| Total memory used base (GB) | Primary Index Shmem + Secondary Index Shmem | Per namespace (live objects only; no tombstone factor yet) | `total_memory_used_base_gb` | Summed over namespaces in engine |

---

## 4. By placement (storage type): memory vs storage contribution

The **same** size (e.g. PI shmem) is either counted toward **memory** or **storage** depending on placement (M = memory, D = disk). PI/SI on disk use **same size as shmem** (product docs: SI “memory space cast to disk”; PI same ballpark).

| Calculation | Formula (business terms) | Applies when / Group | Application function | Notes |
|-------------|---------------------------|----------------------|----------------------|--------|
| Primary index size on disk (GB) | **Same value as** Primary Index Shmem (GB) | When placement.primary == 'D' | Reuse `primary_index_shmem_gb` | No separate disk formula in this planner |
| Secondary index size on disk (GB) | **Same value as** Secondary Index Shmem (GB) | When placement.si == 'D' | Reuse `secondary_index_shmem_gb` | Product docs: “calculated memory space cast to disk” |
| Data effective size (compressed, GB) | Data size (GB) × compression_ratio | When data on device (placement.data == 'D') or when in-memory compression applies (see Version) | In engine: `data_size_gb * compression_ratio` | compression_ratio = compressed/logical; user-editable 0–1 |
| Memory contribution (per namespace) | If primary=='M': + PI shmem; if si=='M': + SI shmem; if data=='M': + data size (see Version for compression) | Per namespace; placement determines which components add to memory | Engine: sum of chosen components | Tombstone applied only to index part (see Tombstone) |
| Storage contribution (per namespace) | If primary=='D': + PI shmem; if si=='D': + SI shmem; if data=='D': + (data size × compression_ratio) | Per namespace; placement determines which components add to storage | Engine: sum of chosen components | |

---

## 5. By Aerospike version (in-memory compression)

When **data** is in memory (placement.data == 'M'), effective size depends on version.

| Calculation | Formula (business terms) | Applies when / Group | Application function | Notes |
|-------------|---------------------------|----------------------|----------------------|--------|
| Data in memory size (GB) | **Pre-7.0:** data_size_gb (uncompressed). **7.0+:** data_size_gb × compression_ratio when in-memory compression enabled | placement.data == 'M' | Engine: apply compression_ratio for 7.0+ (or always if no version input) | Pre-7.0 in-memory effectively uncompressed; 7.0+ can use zstd/LZ4/Snappy |

---

## 6. Tombstone memory

Apply **only to index memory (PI + SI)**, not to data-in-memory. Collectinfo shmem already includes tombstones; do not apply (1 + tombstone_pct) when using collectinfo-derived shmem.

| Calculation | Formula (business terms) | Applies when / Group | Application function | Notes |
|-------------|---------------------------|----------------------|----------------------|--------|
| Index memory (per namespace, GB) | PI_shmem (if on M) + SI_shmem (if on M) | Per namespace; placement primary/si == 'M' | Engine: sum of PI+SI when on M | Live objects only in our formulas |
| Memory with tombstones (per namespace, GB) | index_mem × (1 + tombstone_pct) + data_mem | Per namespace; then sum over namespaces | Engine: `index_mem * (1 + tombstone_pct) + data_mem` | Do not apply factor to data_mem; do not double-count if base is from collectinfo shmem |
| Total memory with tombstones (cluster, GB) | Sum over namespaces of (index_mem × (1 + tombstone_pct) + data_mem) | Namespace summarization | Engine aggregate | |
| Memory utilization with tombstones (%) | 100 × (total memory with tombstones GB ÷ available mem per cluster GB) | Cluster-level output | Engine | |

---

## 7. Namespace summarization (aggregation)

Per-namespace values are combined into cluster-level totals and utilizations.

| Calculation | Formula (business terms) | Applies when / Group | Application function | Notes |
|-------------|---------------------------|----------------------|----------------------|--------|
| Total data stored (GB) | Sum over namespaces of logical data_size_gb | Always (reporting) | Engine: `total_data_stored_gb` | Uncompressed sum for display |
| Total storage used (GB) | Sum over namespaces of storage contribution (PI/SI/data on D with compression where applicable) | Placement-aware | Engine: `total_storage_used_gb` | Used for storage utilization |
| Total memory used base (GB) | Sum over namespaces of memory contribution (with tombstone: index_mem*(1+tombstone_pct)+data_mem) | Placement-aware | Engine | |
| Storage utilization (%) | 100 × (total storage used GB ÷ total usable storage cluster GB) | Cluster-level | `storage_utilization_pct` | Uses placement- and compression-aware total |
| Memory utilization base (%) | 100 × (total memory used base GB ÷ available mem per cluster GB) | Cluster-level | `memory_utilization_base_pct` | Base = before tombstone adjustment in display; engine may use with-tombstone for separate metric |
| Failure storage utilization (%) | 100 × (total data stored or total storage used ÷ failure usable storage GB) | Failure scenario | `failure_storage_utilization_pct` | Use same numerator as storage utilization (placement-aware) |
| Failure memory utilization (%) | 100 × (total memory used GB ÷ (effective_nodes × available memory after overhead per node)) | Failure scenario | Engine | |

---

## 8. Failure scenario

Same formulas as healthy cluster but with **effective nodes** and **failure usable storage** / **failure available memory**. No new formula shapes; only inputs change.

| Calculation | Formula (business terms) | Applies when / Group | Application function | Notes |
|-------------|---------------------------|----------------------|----------------------|--------|
| Failure usable storage (GB) | See Cluster-level only | Failure | `failure_usable_storage_gb` | |
| Failure storage utilization (%) | See Namespace summarization | Failure | `failure_storage_utilization_pct` | |
| Failure memory utilization (%) | 100 × (total memory used ÷ failure available memory) | Failure | Engine | failure_available_mem = effective_nodes × available_after_overhead per node |

---

## 9. Inputs (for reference)

Not formulas but inputs that drive the groups above. Listed so the spreadsheet is complete.

| Input | Description | Grouping relevance |
|-------|--------------|--------------------|
| replication_factor | Replication factor | Per-namespace |
| nodes_per_cluster | Nodes in cluster | Cluster |
| devices_per_node | Devices per node | Cluster |
| device_size_gb | Device size (GB) | Cluster |
| available_memory_gb | Available memory per node (GB) | Cluster |
| overhead_pct | Memory overhead fraction (0–1) | Cluster |
| nodes_lost | Nodes lost in failure scenario | Cluster / Failure |
| master_object_count | Master object count | Per-namespace |
| avg_record_size_bytes | Average record size (bytes) | Per-namespace |
| read_pct, write_pct | Read/write fraction (0–1) | Per-namespace (future: performance) |
| tombstone_pct | Tombstone fraction (0–1) | Per-namespace; affects index memory only |
| si_count | Number of secondary indexes | Per-namespace |
| si_entries_per_object | Average SI entries per object | Per-namespace |
| placement (primary, si, data) | M or D per component | By placement |
| compression_ratio | 0–1 (compressed/logical); user-editable | By placement; version for data on M |
| storage_pattern | HMA, In-Memory, All Flash, DMD, Custom | Derives placement if not Custom |
| stop_writes_at_storage_pct, evict_at_memory_pct, min_available_storage_pct | Thresholds | Future use (e.g. headroom) |

---

## 10. Iteration and validation

- **When you change a formula:** Update the row in this spreadsheet and the corresponding function or engine logic; keep [CALCULATION_CATALOG.md](CALCULATION_CATALOG.md) in sync for legacy cell refs.
- **When a formula depends on version/placement/namespace:** Ensure the “Applies when / Group” column and the section (2–8) are accurate so reviewers can see which variant applies.
- **When in doubt:** Ask for clarification rather than assume; document the decision in Notes.
