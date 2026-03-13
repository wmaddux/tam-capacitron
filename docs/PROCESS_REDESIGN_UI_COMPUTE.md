# Process redesign: UI computes outputs from all input combinations

This document redesigns the process so the **UI correctly computes Storage utilization % and Memory utilization %** from **all combinations of inputs**, using the canonical formulas in the model docs and the collectinfo derivations in the test script.

**References:**
- **[model_calculation_storage_util.md](model_calculation_storage_util.md)** — Pseudo-code for Storage utilization % and how to derive inputs from collectinfo.
- **[model_calculation_mem_util.md](model_calculation_mem_util.md)** — Pseudo-code for Memory utilization % and how to derive inputs from collectinfo.
- **[../tests/test_derivations_mem_util.sh](../tests/test_derivations_mem_util.sh)** — Runs asadm against a collectinfo bundle and parses all inputs needed for both models (cluster + per-namespace).

---

## 1. Unified input model (cluster + namespaces)

One request shape must support:
- **Manual/planning mode:** User sets every value in the UI (sliders, dropdowns, pattern pills).
- **Collectinfo-derived mode:** Load from bundle populates the same shape using the derivations in the model docs and the parsing in the test script.

All of these inputs affect either Storage utilization %, Memory utilization %, or both. The UI must send every field below on every compute request so the backend can handle all combinations.

### 1.1 Cluster-level inputs

| Input | Description | Used in | Source (collectinfo) |
|-------|-------------|--------|----------------------|
| NodesPerCluster | Number of nodes | Storage + Memory | summary → "Cluster Size" |
| DevicesPerNode | Data devices per node | Storage | summary → "Devices Per-Node" |
| DeviceSizeGB | Size of each device (GB) | Storage | summary → Device Total / (Nodes × Devices) |
| StorageOverheadPct | Fraction reserved for FS/metadata/defrag (0–1) | Storage | Manual only |
| StopWritesStoragePct | Stop-writes at storage % (e.g. 70) | Storage | show config namespace &lt;NS&gt; like stop-writes-used-pct (or max-used-pct pre-7) |
| MinAvailStoragePct | Min available storage % (e.g. 10) | Storage | show config namespace &lt;NS&gt; like min-avail-pct |
| MemoryTotalGB_per_node | Total system memory per node (GB) | Memory | summary → "Memory Total" / Nodes |
| StopWritesSysMemoryPct | System memory stop-writes threshold (0–100) | Memory | show config namespace like stop-writes-sys-memory-pct |
| nodes_lost | Nodes lost (failure scenario) | Failure outputs | Manual / optional from collectinfo |

**Note:** StopWritesStoragePct and MinAvailStoragePct can vary per namespace in Aerospike; the test script reads them per namespace. For a single cluster-wide denominator we can use the minimum across namespaces (most conservative) or one representative value. Same idea for StopWritesSysMemoryPct.

### 1.2 Per-namespace inputs

| Input | Description | Used in | Source (collectinfo) |
|-------|-------------|--------|----------------------|
| name | Namespace identifier | Display / export | Config namespace list |
| StoragePattern_ns | 3-char PI/SI/DATA ('M' or 'D') | Storage + Memory | index-type, sindex-type, storage-engine → PI, SI, DATA |
| ReplicationFactor_ns | Replication factor | Storage + Memory | show config namespace &lt;NS&gt; like replication-factor |
| MasterObjectCount_ns | Master objects (cluster sum) | Storage + Memory | show stat namespace &lt;NS&gt; like master_objects → sum |
| AvgRecordSizeBytes_ns | Avg logical record size (bytes) | Storage | device_data_bytes or memory_data_bytes / master_objects (see model doc) |
| CompressionSavingsPct_ns | Fraction of space saved by compression (0–1) | Storage | 1 − compression_ratio from show stat like compression_ratio |
| TombstonePct_ns | Tombstones / master_objects | Storage + Memory | master_tombstones / master_objects |
| IndexBytesWithTombs_ns | Index bytes in memory (PI+SI+set), incl. tombstones | Memory (from collectinfo) | index_used_bytes + sindex_used_bytes + set_index_used_bytes |
| MemDataBytesWithTombs_ns | Data bytes in memory, incl. tombstones | Memory (from collectinfo) | memory_data_bytes or data_used_bytes when DATA='M'; 0 when DATA='D' |

**Two ways to get memory usage per namespace:**
- **From collectinfo:** Use IndexBytesWithTombs_ns and MemDataBytesWithTombs_ns directly (already include tombstones).
- **From manual/planning:** Compute index size from PI+SI formulas (RF, M, SI count, SI entries, etc.) and data size from MasterObjectCount×RF×AvgRecordSize when DATA='M'; then apply tombstone factor to index only (index × (1 + TombstonePct)).

So the request shape should allow either:
- **Observed bytes** (from collectinfo): IndexBytesWithTombs_ns, MemDataBytesWithTombs_ns, and optionally still send workload params for display/export, or
- **Modeled bytes** (manual): No index/mem-data bytes; backend computes from ReplicationFactor, MasterObjectCount, AvgRecordSizeBytes, TombstonePct, StoragePattern, SI params, etc.

The backend can treat “if index_bytes and mem_data_bytes provided for ns → use them; else compute from workload params” so both modes work.

---

## 2. Output formulas (canonical)

The engine must implement the exact logic in the model docs so that all input combinations produce correct outputs.

### 2.1 Storage utilization %

**Source:** [model_calculation_storage_util.md](model_calculation_storage_util.md).

- **Usable device capacity (denominator):**  
  RawDeviceGB_cluster = Nodes × DevicesPerNode × DeviceSizeGB  
  MaxDataPct = min(StopWritesStoragePct, 100 − MinAvailStoragePct)  
  UsableDeviceGB_cluster = RawDeviceGB_cluster × (1 − StorageOverheadPct) × (MaxDataPct / 100)

- **Per-namespace device data (numerator):**  
  LiveRecs_ns = MasterObjectCount_ns × ReplicationFactor_ns  
  TotalRecs_ns = LiveRecs_ns × (1 + TombstonePct_ns)  
  EffectiveRecordSizeBytes_ns = AvgRecordSizeBytes_ns × (1 − CompressionSavingsPct_ns)  
  DataBytes_ns = TotalRecs_ns × EffectiveRecordSizeBytes_ns  
  DataGB_ns = DataBytes_ns / BytesPerGB  
  If third char of StoragePattern_ns == 'D': DeviceDataGB_ns = DataGB_ns, else 0

- **Total device data:**  
  TotalDeviceDataGB_all_ns = sum over namespaces of DeviceDataGB_ns

- **Output:**  
  Storage utilization % = (TotalDeviceDataGB_all_ns / UsableDeviceGB_cluster) × 100

So: **only data on device** (DATA='D') contributes to the numerator; PI/SI on disk are not in this formula. Usable capacity is reduced by StorageOverheadPct and by MaxDataPct (stop-writes and min-avail).

### 2.2 Memory utilization %

**Source:** [model_calculation_mem_util.md](model_calculation_mem_util.md).

- **System memory budget (denominator):**  
  SysMemBudgetBytes_cluster = NodesPerCluster × MemoryTotalGB_per_node × (StopWritesSysMemoryPct / 100) × BytesPerGB

- **Per-namespace memory (with tombstones):**  
  If from collectinfo: TotalMemBytesWithTombs_ns = IndexBytesWithTombs_ns + MemDataBytesWithTombs_ns  
  If from manual: compute Index (PI+SI) and MemData (when DATA='M') then Index×(1+TombstonePct)+MemData (or equivalent).

- **Per-namespace memory (without tombstones):**  
  IndexBytesNoTombs_ns = IndexBytesWithTombs_ns / (1 + TombstonePct_ns)  
  MemDataBytesNoTombs_ns = MemDataBytesWithTombs_ns / (1 + TombstonePct_ns)  
  TotalMemBytesNoTombs_ns = IndexBytesNoTombs_ns + MemDataBytesNoTombs_ns

- **Totals:**  
  Sum over namespaces of TotalMemBytesWithTombs_ns and TotalMemBytesNoTombs_ns

- **Outputs:**  
  Memory utilization with tombstones % = (TotalMemBytesWithTombs_all_ns / SysMemBudgetBytes_cluster) × 100  
  Memory utilization without tombstones % = (TotalMemBytesNoTombs_all_ns / SysMemBudgetBytes_cluster) × 100

---

## 3. Data flow: UI → API → engine

1. **UI** holds state for cluster + list of namespaces. Every field in sections 1.1 and 1.2 is editable or display-only as appropriate (e.g. name, StoragePattern, ReplicationFactor, MasterObjectCount, AvgRecordSizeBytes, CompressionSavingsPct, TombstonePct; cluster: Nodes, Devices, DeviceSize, StorageOverheadPct, StopWritesStoragePct, MinAvailStoragePct, MemoryTotalGB_per_node, StopWritesSysMemoryPct).

2. **Load from collectinfo:**  
   - Run the same derivations as [test_derivations_mem_util.sh](../tests/test_derivations_mem_util.sh) (or call an ingestor that implements the same parsing).  
   - Produce one cluster object and one namespace object per namespace, with every input above filled (including IndexBytesWithTombs_ns, MemDataBytesWithTombs_ns when from collectinfo).  
   - UI replaces its state with this cluster + namespaces and then calls compute.

3. **Compute request:**  
   - POST /api/compute-v2 with body `{ "cluster": { ... }, "namespaces": [ { ... }, ... ] }` where cluster and each namespace contain **all** inputs from sections 1.1 and 1.2 (plus any display-only fields).  
   - Thresholds that are per-namespace in Aerospike (StopWritesStoragePct, MinAvailStoragePct, StopWritesSysMemoryPct) can be sent per-namespace; the engine uses a cluster-wide rule (e.g. minimum across namespaces) for the single denominator when the model doc expects one value.

4. **Engine:**  
   - Implements the pseudo-code in [model_calculation_storage_util.md](model_calculation_storage_util.md) for Storage utilization %.  
   - Implements the pseudo-code in [model_calculation_mem_util.md](model_calculation_mem_util.md) for Memory utilization % (with and without tombstones).  
   - For memory: if namespace has IndexBytesWithTombs_ns and MemDataBytesWithTombs_ns, use them; else compute from workload params (PI+SI formulas + data when DATA='M') and apply tombstone factor to index only.

5. **Response:**  
   - Returns storage_utilization_pct, memory_utilization_with_tombstones_pct, memory_utilization_without_tombstones_pct (or equivalent names), plus any other outputs (failure scenario, per-namespace breakdown, etc.).

6. **UI** displays the returned outputs and keeps Data growth / Performance as placeholders until specified.

---

## 4. Aligning with the test script and model docs

- **test_derivations_mem_util.sh** already parses: NodesPerCluster, DevicesPerNode, DeviceSizeGB, MemoryTotalGB_per_node, per-namespace StopWritesStoragePct, MinAvailStoragePct, StopWritesSysMemoryPct, StoragePattern_ns, ReplicationFactor_ns, MasterObjectCount_ns, AvgRecordSizeBytes_ns, CompressionSavingsPct_ns, TombstonePct_ns, IndexBytesWithTombs_ns, MemDataBytesWithTombs_ns.  
- The **ingestor** (or load-collectinfo path) should output the same structure so the UI can send it to compute-v2.  
- **API request/response** and **engine** should use the same names and formulas as the model docs so that:  
  - Manual-only inputs → engine computes everything from workload + pattern.  
  - Collectinfo-derived inputs (with optional index/mem-data bytes) → engine uses observed bytes when present.  
  - All combinations (e.g. one namespace from collectinfo with bytes, one namespace manual-only) are supported.

---

## 5. Checklist for implementation (after spreadsheet is fixed)

- [ ] **Model (core/model.py):** Extend ClusterInputs and NamespaceInputs with all fields in sections 1.1 and 1.2 (StorageOverheadPct, StopWritesStoragePct, MinAvailStoragePct, StoragePattern_ns, CompressionSavingsPct_ns, MemoryTotalGB_per_node, StopWritesSysMemoryPct; optional IndexBytesWithTombs_ns, MemDataBytesWithTombs_ns per namespace).
- [ ] **Engine (core/engine.py):** Implement Storage utilization % per model_calculation_storage_util.md (usable capacity with MaxDataPct; only data on device in numerator; TotalRecs with TombstonePct; EffectiveRecordSize with CompressionSavingsPct). Implement Memory utilization % per model_calculation_mem_util.md (SysMemBudget; use observed bytes when provided, else compute from workload; with/without tombstones).
- [ ] **API (app/main.py):** Extend ClusterBody and NamespaceBody to accept all new fields; map to model; return new outputs.
- [ ] **Ingest / load-collectinfo:** Populate cluster + namespaces from bundle using the same parsing logic as test_derivations_mem_util.sh (and the collectinfo sections of the two model docs).
- [ ] **UI (app/static/index.html):** Send all cluster and namespace fields in the compute-v2 payload; display storage_utilization_pct and memory_utilization_* from response; keep Parameter help and Show my work in sync with the model docs.
- [ ] **Calculation spreadsheet:** Update [CALCULATION_SPREADSHEET.md](CALCULATION_SPREADSHEET.md) so Storage utilization % and Memory utilization % sections match the formulas in the model docs (including MaxDataPct, only-data-on-device, and memory with/without tombstones).

No code changes until the calculation spreadsheet is correct; this doc defines the target process and data flow.
