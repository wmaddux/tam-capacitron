# Calculation catalog

All capacity calculations implemented in this application are derived from two spreadsheets. This catalog is the **mapping reference** from spreadsheet cells to application logic. Cell references are used here only for audit and traceability; they do not appear in application code.

**Sources:**
- **Capacity_planner (fidelity workbench)** – calcManual, worksheetManual, Advanced settings (workbook no longer in repo; mapping preserved below for traceability).
- **Tool_Aerospike_Sizing_Estimator_(10_14).xlsx** – In repo root when present. Workload, AWS, Custom, Miscellaneous (future use).

---

## Capacity planner (fidelity workbench)

### Inputs (worksheetManual → engine)

| Logical input | worksheetManual | Description |
|---------------|-----------------|-------------|
| replication_factor | F6 | Replication factor |
| nodes_per_cluster | F7 | Nodes per cluster |
| devices_per_node | F8 | Devices per node |
| device_size_gb | F9 | Device size (GB) |
| available_memory_gb | F12 | Available memory per node (GB, raw) |
| overhead_pct | F13 | Memory overhead fraction (0–1) |
| master_object_count | F16 | Master object count |
| avg_record_size_bytes | F17 | Average record size (bytes) |
| read_pct | F18 | Read fraction (0–1) |
| write_pct | F19 | Write fraction (0–1) |
| tombstone_pct | F20 | Tombstone fraction (0–1) |
| si_count | F21 | Number of secondary indexes |
| si_entries_per_object | F22 | Average SI entries per object |
| nodes_lost | F25 | Nodes lost in failure scenario |

### Constants (fixed in workbook, used in formulas)

| Constant | calcManual ref | Value | Use |
|----------|----------------|-------|-----|
| MTU_BYTES | C21 | 1500 | MTU / packet size |
| HEADER_OVERHEAD | C22 | 320 | Header overhead |
| FRAGMENTATION_FACTOR | C23 | 0.024 | (1 − C23) = usable storage fraction |
| RECORD_METADATA_BYTES | — | 64 | Primary Index Shmem: 64 bytes per replicated object |
| SI_ENTRY_SIZE_BYTES (S) | — | 32 | Average SI entry size (bytes); collectinfo-style |
| SI_FILL_FACTOR (F) | — | 0.75 | SI index fill factor (0–1) |
| SI_CUSHION_PER_INDEX_PER_NODE_BYTES (H) | — | 16,777,216 | Fixed cushion per index per node (16 MiB); collectinfo-style |
| (others) | C40, C41, C42 | 21, 0.75, 16 | Used in memory/storage limits |

### Calculations (calcManual and related)

| Calculation | Application function | Formula (business terms) | Source cell(s) |
|-------------|-----------------------|--------------------------|----------------|
| Device total storage (TB) | `device_total_storage_tb` | (Nodes per cluster × devices per node × device size GB) ÷ 1024 | C9 = (C6×C7×C8)/1024 |
| Total device count | `total_device_count` | Nodes per cluster × devices per node | C10 = C6×C7 |
| Available memory after overhead (GB) | `available_memory_after_overhead_gb` | Available memory per node × (1 − overhead pct) | C18 = C14×(1−C15) |
| Memory overhead (GB) | `memory_overhead_gb` | Available memory − available after overhead | C19 = C14−C18 |
| Total objects (replicated) | `total_objects` | Replication factor × master object count | C36 = C5×C27 |
| Data size (GB) | `data_size_gb` | (Master objects × replication × avg record size bytes) ÷ 1024³ | C54 = (C27×C5×C28)/1024³ |
| Usable storage per node (GB) | `usable_storage_per_node_gb` | Devices per node × device size GB × (1 − fragmentation factor) | C55 term: C7×C8×(1−C23) |
| Total usable storage cluster (GB) | `total_usable_storage_cluster_gb` | Nodes × devices per node × device size GB × (1 − fragmentation factor) | C55 = C6×C7×C8×(1−C23) |
| Available memory per cluster (GB) | `available_mem_per_cluster_gb` | Nodes per cluster × available memory after overhead per node | C59 = C6×C18 |
| Primary Index Shmem (GB) | `primary_index_shmem_gb` | (RF × master object count × 64 bytes) ÷ 1024³ | Per namespace; 64 = RECORD_METADATA_BYTES |
| Secondary Index Shmem (GB) | `secondary_index_shmem_gb` | Entries per index = M×RF×E; Data bytes per index = Entries×(S/F); Data (all) = N×data per index; Cushion = N×H×K; Total SI = Data + Cushion; ÷ 1024³ | Collectinfo-style: M, RF, E, N, K; S, F, H = constants |
| Total memory used base (GB) | `total_memory_used_base_gb` | Primary Index Shmem + Secondary Index Shmem (per namespace); engine sums over namespaces | Replaces previous C37; aligns with Aerospike shmem |
| Storage utilization (%) | `storage_utilization_pct` | 100 × (data stored GB ÷ total available storage GB) | C53 = C54/C55 (as %) |
| Memory utilization base (%) | `memory_utilization_base_pct` | 100 × (memory used base GB ÷ available mem per cluster GB) | C68 = C69/C71 |
| Effective nodes (failure) | `effective_nodes` | Nodes per cluster − nodes lost | C70 = C6−C46 |
| Failure usable storage (GB) | `failure_usable_storage_gb` | Effective nodes × devices per node × device size GB × (1 − fragmentation factor) | C71 = (C6−C46)×C7×C8×(1−C23) |
| Failure storage utilization (%) | `failure_storage_utilization_pct` | 100 × (data stored GB ÷ failure total available storage GB) | Same as healthy, with failure available |

### Performance (Capacity planner v3.0 – customer spreadsheet)

| Calculation | Application function | Formula (business terms) | Source |
|-------------|----------------------|--------------------------|--------|
| Total IOPS per Node (K) | `total_iops_per_node_k` | Devices per node × IOPS per disk (K) | Capacity planner v3.0 Performance |
| Estimated IOPS (K) per cluster | `estimated_iops_per_cluster_k` | Nodes per cluster × Total IOPS per Node (K) | Capacity planner v3.0 Performance |
| Reads per second (k) | `reads_per_second_k` | Avg Read pct × Estimated IOPS (K) per cluster | Capacity planner v3.0 Performance |
| Writes per second (k) | `writes_per_second_k` | Avg Write pct × Estimated IOPS (K) per cluster | Capacity planner v3.0 Performance |
| Read Bandwidth (MB/s) | `read_bandwidth_mbs` | Reads per second (k) × 1000 × Avg record size / 1024² | Capacity planner v3.0 Performance |
| Write Bandwidth (MB/s) | `write_bandwidth_mbs` | Writes per second (k) × 1000 × Avg record size / 1024² | Capacity planner v3.0 Performance |
| Total Throughput per Node (MB/s) | `total_throughput_per_node_mbs` | Devices per node × Throughput per disk (MB/s) | Capacity planner v3.0 Performance |
| Peak Throughput per cluster (MB/s) | `peak_throughput_per_cluster_mbs` | Total Throughput per Node (MB/s) × Nodes per cluster | Capacity planner v3.0 Performance |

### Placement-aware capacity (memory vs storage by primary / SI / data)

Per-namespace placement determines where primary index (PI), secondary index (SI), and data live: **M** = in memory (shmem for indexes), **D** = on device (storage).

- **Primary index:** M → contributes `primary_index_shmem_gb` to namespace memory; D → same size (shmem proxy per product docs) to namespace storage.
- **Secondary index:** M → contributes `secondary_index_shmem_gb` to namespace memory; D → same size (shmem cast to disk) to namespace storage.
- **Data:** M → contributes (logical data size × compression_ratio) to namespace memory; D → contributes (logical data size × compression_ratio) to namespace storage. In Database 7.0+, in-memory data can use storage compression; the same ratio is applied for both M and D.

**Tombstones:** Applied only to index memory: `memory_with_tombstones = index_mem × (1 + tombstone_pct) + data_mem`. Collectinfo-derived shmem already includes tombstones; do not apply the factor again if ingesting collectinfo.

**Aggregation:** `total_memory_used_base_gb` = sum of per-namespace memory (index + data on M, with tombstone factor on index). `total_storage_used_gb` = sum of per-namespace storage (PI + SI + data on D). Storage utilization = 100 × total_storage_used_gb / total_usable_storage_gb.

### Compression (effective size)

Compression is a **user-editable 0–1 factor**: **compression_ratio** = compressed_size / logical_size (e.g. 0.6 means 60% of logical size after compression).

- **Effective data size:** `effective_data_gb = data_size_gb × compression_ratio`. Used for both storage (data on D) and memory (data on M when in-memory compression applies, e.g. 7.x).
- **Presets (suggested ranges; workload-specific):** Off = 1.0 (no savings); LZ4 ≈ 0.6–0.7 (e.g. Aerospike ~0.659); Zstandard ≈ 0.3–0.5 (e.g. level 1 ~0.33–0.38). Parameter help should state values are workload-dependent.

### Advanced settings (future)

| Calculation | Description | Source |
|-------------|-------------|--------|
| AllowedUsedFraction (evict, stop-writes, min-avail, defrag) | Storage thresholds derived from config | Advanced settings C5–C8, E10–E13 |
| RequiredStorageBytes_overall | Data bytes ÷ min allowed fraction | E17 |
| RequiredStorageGB_defrag | Required storage in GB | E18 |

---

## Tool_Aerospike_Sizing_Estimator (10_14)

Multi-sheet workbook for workload sizing, disk/RAM/IOPS estimation, and (AWS or Custom) instance selection. Used in later phases; captured here for mapping. Sheets: **Workload**, **AWS**, **Custom**, **Miscellaneous**.

### Miscellaneous sheet – constants and units

Used by Workload, AWS, and Custom. Named ranges and fixed values.

| Parameter / constant | Description | Source / formula |
|---------------------|-------------|------------------|
| PIEntrySize (Primary Index Entry Size) | Bytes per primary index entry | B3 / 64 |
| SIEntrySize (Secondary Index Entry Size) | Bytes per SI entry | B4 / 21 |
| SIOverhead (Secondary Index Overhead) | Overhead in bytes | B5 = 16×1024² |
| WriteBlockSize | Write block size bytes | B6 = 8×MB |
| DiskBlockSize | Disk block size | B7 / 4096 |
| RecordOverhead | Record overhead bytes | B8 / 64 |
| SprigSize | Sprig size bytes | B11 / 4096 |
| Partitions | Number of partitions | B12 / 4096 |
| RecordsPerSprig | Records per sprig | B13 = SprigSize/PIEntrySize |
| PIFillFactor (Primary Index Fill Factor) | Fill factor 0–1 | B14 / 0.5 |
| SIBTreeNodeCapacity | Items per SI B-tree leaf | B15 / 227 |
| SIFillFactor | SI fill factor | B16 / 0.75 |
| SecondsInAYear | Seconds in a year | B24 = days×hours×min×sec (B19:B22) |
| KB, MB, GB, TB | Unit powers of 1024 | B26 = 1024^1, B27 = 1024^2, B28 = 1024^3, B29 = 1024^4 |
| DefragOverhead | Defrag overhead fraction | Workload B57 / 0.5 |
| MemoryUtilisation | Memory utilisation target | Workload B58 / 0.75 |
| DiskUtilisation | Disk utilisation target | Workload B59 / 0.95 |

### Workload sheet – parameters (per use case 1–5)

Each use case (namespace/set) can have its own values. Column C = Use case 1, D = 2, etc.

| Parameter | Description | Typical source column |
|-----------|-------------|------------------------|
| Replication Factor (RF_1 … RF_5) | Replication factor per use case | C7–G7 |
| Average Object size (B) (AvgObjSize1…5) | Average object size bytes | C9–G9 |
| Object Count (ObjCount1…5) | Object count | C10–G10 |
| Average Number of Objects per Record (AvgObjPerRecord1…5) | Objects per record | C12–G12 |
| Compression Reduction (CompressionReductionObj1…5) | Compression ratio 0–1 | C13–G13 |
| Number of Secondary Indexes (NumberOfSIs1…5) | SI count | C15–G15 |
| Average SI Entry Per Object (SICoverage1…5) | SI entries per object | C16–G16 |
| Peak SI Query | Peak SI queries/sec | C17–G17 |
| Not Found Rate (NotFoundRate1…5) | Read not-found rate | C19–G19 |
| Page Cache Hit Rate (PageCacheRate1…5) | Page cache hit rate | C20–G20 |
| Average Reads Per Second (AvgObjRPS1…5) | Avg reads/sec | C21–G21 |
| Peak Reads Per Second (PeakObjRPS1…5) | Peak reads/sec | C22–G22 |
| Average Writes Per Second (AvgObjWPS1…5) | Avg writes/sec | C24–G24 |
| Peak Writes Per Second (PeakObjWPS1…5) | Peak writes/sec | C25–G25 |
| Primary Index Storage (PIStorage1…5) | "Ram" or "Disk" | C27–G27 |
| Secondary Index Storage (SIStorage1…5) | "Ram" or "Disk" | C28–G28 |
| Data Storage (DataStorage1…5) | "Ram" or "Disk" | C29–G29 |
| Cached Levels of SI on Disk BTree (TargetCachedLevel1…5) | Cached B-tree levels | C31–G31 |

### Workload sheet – calculations (resource size and IO)

| Calculation | Formula (business terms) | Source |
|-------------|--------------------------|--------|
| Average Record Size (per use case) | Average object size × average objects per record | B38 = AvgObjSize×AvgObjPerRecord |
| Unique Data Size (GB) (per use case) | Object count × average object size ÷ GB | B39 = ObjCount×AvgObjSize/GB |
| Record Count (M) (per use case) | Object count ÷ average objects per record | B40 = ObjCount/AvgObjPerRecord |
| Primary index size in RAM (GB) | If PI storage = Ram: record count × PI entry size ÷ GB; else 0 | B42 |
| Sprigs Required Per Partition | If PI on disk: 2^ceiling(log(record_count / (RecordsPerSprig×PIFillFactor)) / log(2)) | B43 |
| Primary index size on disk (GB) | If PI on disk: sprigs per partition × partitions × sprig size ÷ GB | B44 |
| SI entries (per use case) | If SI count > 0: object count × SI coverage; else 0 | B46 |
| Each SI size (GB) | (SI entries × SI entry size + SI overhead) ÷ GB | B47 |
| Total SI size (GB) | Each SI size × number of SIs | B48 |
| SI on disk B-tree depth | If SI on disk: log(SI entries / partitions) / log(SI node capacity × fill factor) | B49 |
| Data size with overheads (GB) | (Avg record size×(1−compression)+RecordOverhead) × record count ÷ GB | B51 |
| Unique Data Size total (GB) | Sum of unique data across use cases | B54 |
| Minimum RAM required (GB) | Sum of PI in RAM + SI in RAM (with RF), then × multiplier | B62 |
| Minimum Disk required (GB) | Sum of PI on disk + SI on disk + data on disk (with RF), then × multiplier | B63 |
| Disk to Ram ratio | Min disk ÷ min RAM (or "Minimal Ram" if RAM near 0) | B64 |
| Page cache size for on-disk SI (GB) | If SI on disk: number of SIs × 227^min(target cached levels, SI depth) × … | B65 |
| Data write I/Os per write | If data on disk: 1 × RF (per use case) | B72 |
| Data read I/Os per read | If data on disk: (1−not found rate)×(1−page cache rate) | B73 |
| PI write I/Os per insert | If PI on disk: 2 × RF | B75 |
| PI read I/Os per insert | If PI on disk: 3 × RF | B76 |
| PI read I/Os per lookup | If PI on disk: 1 | B77 |
| SI write I/Os per insert | If SI on disk: 1 × RF | B79 |
| SI read I/Os per insert | If SI on disk: ceiling(log(SI entries/partitions, SI node capacity)) | B80 |
| SI read I/Os per lookup | If SI on disk: partitions × max(log …) | B81 |
| Peak disk write throughput (MB/s) | Peak obj writes × data write I/Os per write × (record size with compression) ÷ block size / MB | B85 |
| Peak disk read throughput (MB/s) | Peak obj reads × data read I/Os per read × ceiling(record size/block) / MB | B86 |
| Peak disk write IOPS (K) | Ceiling(peak write throughput in bytes / block size) / 1000 | B88 |
| Peak disk read IOPS (K) | Peak reads × read I/Os per read × ceiling(record size/block) / 1000 | B89 |
| Total peak write throughput (MB/s) | Sum of peak disk write throughput across use cases | B93 |
| Total peak read throughput (MB/s) | Sum of peak disk read throughput across use cases | B94 |
| Total peak write IOPS (K) | Sum of peak disk write IOPS | B96 |
| Total peak read IOPS (K) | Sum of peak disk read IOPS | B97 |

### AWS sheet – parameters and instance lookup

| Parameter | Description | Source |
|-----------|-------------|--------|
| ResiliencyTarget | "None", "Rack/AZ", "Node" | C3 |
| ToleratedNodeFailuresCount | Number of node failures tolerated | C4 |
| RacksOrAvailabilityZonesCount (AZ) | Racks or AZs | C5 |
| ToleratedAZRackFailuresCount | AZ/rack failures tolerated | C6 |
| AllowReadFromNearestRackAZ | 0/1 | C7 |
| InstanceType | EC2 instance type name (e.g. m3.medium) | C10 |
| InstanceCount (Number of Instances) | Number of instances | C11 |
| DiskOverprovisioning | Fraction of disk to reserve (e.g. 0.15) | C12 |
| InstanceRamSize | RAM per instance (GB) – from VLOOKUP | F4 = VLOOKUP(InstanceType, AWS!V4:AB780, 3) |
| InstanceCpuCount | vCPUs – from VLOOKUP | (referenced) |
| InstanceDiskCount | Disks per instance – from VLOOKUP | F5 = VLOOKUP(…, 5) |
| InstanceDiskSize | Disk size per disk (GB) – from VLOOKUP | F4 col 4 × count |
| InstanceThroughput | Throughput per instance (MB/s) | F7/F10 |
| InstanceIOPS | IOPS per instance (K) | F8/F9 |
| Multiplier | Resilience multiplier: None=1, Rack/AZ = AZ/(AZ−C6), Node = InstanceCount/(InstanceCount−C4) | C15 |
| MinRam, MinDisk | From Workload!B62, B63 | C19, C20 |
| TotalGuaranteedRam | MinRam × Multiplier | C19 |
| TotalGuaranteedDisk | MinDisk × Multiplier | C20 |
| Total RAM (GB) | InstanceCount × InstanceRamSize | F19 |
| Total DISK (GB) | InstanceCount × InstanceDiskSize × (1 − DiskOverprovisioning) | F20 |
| DomainModelDiskToRamRatio | MinDisk/MinRam (Workload B64) | C21 |
| Peak Throughput (MB/s) | (Peak read + peak write throughput) × Multiplier | C23 |
| Peak IOPS (K) | (Peak read IOPS + peak write IOPS×RF_1) × Multiplier | C24 |
| PageCacheSize | From Workload (B26) | C26 |
| AWSDiskIOPS, AWSDiskThroughput | Per-disk IOPS (K) and throughput (MB/s) – constants or lookup | F8, F7 |
| Instance monthly reserved rate | VLOOKUP(InstanceType, …, 7) | F12 |
| Infrastructure monthly | F12 × C11 | C41 |
| Infrastructure annual | C41 × 12 | C42 |
| AZ Data Transfer Cost Per GB | Cost per GB egress | C34 |
| AZTransferByWrite, AZTransferByWriteReplication, AZTransferByRead | Egress volumes (GB) for write, replication, read | C30, C31, C32 |
| Annual write/read egress cost | (Write+Replication)×Cost, Read×Cost | C35, C36 |
| Networking annual | Sum(C35:C36) | C45 |
| Total monthly / annual | C41+C44 (networking monthly), etc. | C47, C48 |

AWS sheet also contains a large table (V4:AB780) of instance types with columns for vCPU, RAM, disk count, disk size, throughput, IOPS, monthly rate, etc., used by VLOOKUP.

### Custom sheet – parameters (non-AWS hardware)

| Parameter | Description | Source |
|-----------|-------------|--------|
| ResiliencyTarget | "None", "Rack/AZ", "Node" | C3 |
| ToleratedNodeFailuresCount | Node failures tolerated | C4 |
| RacksOrAvailabilityZonesCount (AZ) | Racks or AZs | C5 |
| ToleratedAZRackFailuresCount | AZ/rack failures | C6 |
| AllowReadFromNearestRackAZ | 0/1 | C7 |
| InstanceCount (Number of Nodes) | Number of nodes | C10 |
| InstanceCpuCount (Number of vCPUs) | vCPUs per node | C12 |
| InstanceRamSize (Ram GB) | RAM per node (GB) | C13 |
| InstanceDiskCount (Number of Disks) | Disks per node | C14 |
| Each Disk Size (GB) | Disk size per disk (GB) | C15 |
| DiskOverprovisioning | Fraction reserved | C16 |
| MonthlyRate | Monthly rate per node (cost) | C17 |
| InstanceThroughput (Throughput per Disk MB/s) | Throughput per disk | C18 |
| InstanceIOPS (IOPS per Disk K) | IOPS per disk (K) | C19 |
| TotalDiskSize (GB) | Each disk size × number of disks | C20 = C15×C14 |
| Total IOPS (K) | IOPS per disk × number of disks | C21 = C19×C14 |
| Total Throughput (MB/s) | Throughput per disk × number of disks | C22 = C18×C14 |
| Multiplier | Same logic as AWS (None, Rack/AZ, Node) | C25 |
| TotalGuaranteedRam, TotalGuaranteedDisk | MinRam×Multiplier, MinDisk×Multiplier (from Workload) | C29, C30 |
| Total RAM (GB) | InstanceCount × InstanceRamSize | C29 |
| Total DISK (GB) | InstanceCount × InstanceDiskSize × (1 − DiskOverprovisioning) | C30 |
| Peak Throughput, Peak IOPS | (Workload totals) × Custom!Multiplier | C33, C34 |
| AZTransferCost, egress costs | Same structure as AWS | C44, C45, C46 |
| Infrastructure monthly / annual | C17×C10, ×12 | C51, C52 |
| Total monthly / annual | Infrastructure + networking | C57, C58 |

### Cross-workbook references (for later integration)

- **Workload → AWS/Custom:** MinRam (Workload B62), MinDisk (Workload B63), DomainModelDiskToRamRatio (Workload B64), UniqueData (Workload B54), PeakDiskReadThroughput, PeakDiskWriteThroughput, PeakReadIOPS, PeakWriteIOPS (Workload totals), PageCacheSize (Workload B26).
- **Miscellaneous → Workload/AWS/Custom:** GB, MB, PIEntrySize, SprigSize, Partitions, RecordsPerSprig, SIBTreeNodeCapacity, SIEntrySize, SIOverhead, SecondsInAYear, etc.
- **Resilience multiplier:** Used to scale MinRam and MinDisk (and thus instance count or node count) when tolerating node or AZ failures. Formula: None → 1; Rack/AZ → AZ/(AZ−ToleratedAZRackFailuresCount); Node → InstanceCount/(InstanceCount−ToleratedNodeFailuresCount).
