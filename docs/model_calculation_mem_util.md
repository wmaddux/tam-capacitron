Pseudo-code for calculating MEMORY UTILIZATION % (INDEXES) (w and w/o tombstones)


# CONSTANT
BytesPerGB = 1024^3

############################################
# CLUSTER‑LEVEL INPUTS (TOTAL MEMORY)
############################################

NodesPerCluster            # number of nodes in cluster
MemoryTotalGB_per_node     # total system memory per node (GB)
StopWritesSysMemoryPct     # stop-writes-sys-memory-pct (0–100)

############################################
# NAMESPACE‑LEVEL INPUTS (AFFECT MemoryUtil_%)
############################################

StoragePattern_ns          # 3-char PI/SI/DATA pattern, each char is 'M' or 'D'
                           #   MMM = PI in M,  SI in M,  DATA in M
                           #   MMD = PI in M,  SI in M,  DATA in D
                           #   DDD = PI in D,  SI in D,  DATA in D
                           #   DMD = PI in D,  SI in M,  DATA in M
                           #   CUSTOM = any other 3-char combination; DATA = 3rd char

IndexBytesWithTombs_ns     # index bytes in memory (PI + SI + set index), incl. tombstones
MemDataBytesWithTombs_ns   # data bytes in memory (record bodies), incl. tombstones
                           # for planning:
                           #   if DATA (3rd char) == 'D', you may set this to 0
                           #   if DATA == 'M', set to modeled in-memory data size

TombstonePct_ns            # tombstones as fraction of live masters for namespace ns
                           # TombstonePct_ns ≈ master_tombstones / master_objects

############################################
# 1. EFFECTIVE SYSTEM MEMORY BUDGET (FOR ASD)
############################################

SysMemBudgetBytes_cluster =
    NodesPerCluster
  * MemoryTotalGB_per_node
  * (StopWritesSysMemoryPct / 100.0)
  * BytesPerGB

############################################
# 2. MEMORY USAGE (WITH / WITHOUT TOMBSTONES)
############################################

# 2.1 Per-namespace components

# Actual (with tombstones) are direct inputs:
#   IndexBytesWithTombs_ns
#   MemDataBytesWithTombs_ns

# Approximate view if there were no tombstones:
IndexBytesNoTombs_ns =
    IndexBytesWithTombs_ns / (1 + TombstonePct_ns)

MemDataBytesNoTombs_ns =
    MemDataBytesWithTombs_ns / (1 + TombstonePct_ns)

TotalMemBytesWithTombs_ns =
    IndexBytesWithTombs_ns + MemDataBytesWithTombs_ns

TotalMemBytesNoTombs_ns =
    IndexBytesNoTombs_ns + MemDataBytesNoTombs_ns

# 2.2 Aggregate across namespaces

TotalMemBytesWithTombs_all_ns =
    sum over all namespaces ns of TotalMemBytesWithTombs_ns

TotalMemBytesNoTombs_all_ns =
    sum over all namespaces ns of TotalMemBytesNoTombs_ns

############################################
# 3. TOTAL MEMORY UTILIZATION % (INDEX + DATA)
############################################

MemoryUtil_with_tombstones_% =
    ( TotalMemBytesWithTombs_all_ns / SysMemBudgetBytes_cluster ) * 100

MemoryUtil_without_tombstones_% =
    ( TotalMemBytesNoTombs_all_ns / SysMemBudgetBytes_cluster ) * 100






When deriving inputs from collectinfo, use the following methods (may differ between Aerospike versions)


cluster_inputs:
  - name: NodesPerCluster
    description: Number of nodes in the Aerospike cluster
    command: asadm -cf "<bundle>" -e "summary"
    parse: |
      Find the line starting with "Cluster Size".
      NodesPerCluster = integer value on that line.

  - name: MemoryTotalGB_per_node
    description: Total system memory per node (GB)
    command: asadm -cf "<bundle>" -e "summary"
    parse: |
      If "Memory Total" is present:
        - Parse the line starting with "Memory Total".
          Example: "Memory Total             125.0 GB"
          MemoryTotalGB_cluster = numeric GB value on that line.
        - MemoryTotalGB_per_node = MemoryTotalGB_cluster / NodesPerCluster

      If "Memory Total" is not present (N/A):
        - Treat MemoryTotalGB_per_node as a planner input
          (e.g. from instance type / node specs).

  - name: StopWritesSysMemoryPct
    description: System memory stop-writes threshold (stop-writes-sys-memory-pct, 0–100)
    command: asadm -cf "<bundle>" -e "show config namespace like stop-writes-sys-memory-pct -flip"
    parse: |
      For each namespace <NS>, parse "stop-writes-sys-memory-pct".
      For a single cluster-wide value, take the minimum across namespaces
      (most conservative), or a representative if they are identical.
      If no value is found, default StopWritesSysMemoryPct = 100.

namespace_inputs:
  - name: StoragePattern_ns
    description: 3-char PI/SI/DATA placement pattern (M or D for each) for MEMORY
    command: asadm -cf "<bundle>" -e "show config namespace <NS> -flip"
    parse: |
      From the namespace config for <NS>:

        1) Primary index (PI) → 1st char:
             if "index-type" == "flash" then PI = 'D'
             else PI = 'M'

        2) Secondary index (SI) → 2nd char:
             if "sindex-type" == "flash" then SI = 'D'
             else SI = 'M'

        3) Data placement (MEMORY semantics) → 3rd char:
             if storage-engine is "memory { ... }" (with or without persistence)
               then DATA = 'M'
             if storage-engine is "device { ... }" or "pmem { ... }"
               then DATA = 'D'

      StoragePattern_ns = PI + SI + DATA

      For MemoryUtil_%:
        - DATA='M' means record bodies live in RAM (in-memory namespaces,
          including 7.x in-memory+persist).
        - DATA='D' means record bodies live on device; RAM holds only indexes
          and caches.

  - name: IndexBytesWithTombs_ns
    description: Index bytes in memory (PI + SI + set indexes), including tombstones
    command: asadm -cf "<bundle>" -e "show stat namespace <NS> like index_used_bytes|sindex_used_bytes|set_index_used_bytes -flip"
    parse: |
      For each namespace <NS> and node:
        index_used_bytes      = primary index bytes
        sindex_used_bytes     = secondary index bytes (if present)
        set_index_used_bytes  = set index bytes (if present)

      For <NS>:
        IndexBytesWithTombs_ns =
            sum across all nodes of:
              (index_used_bytes + sindex_used_bytes + set_index_used_bytes)

      This value is the in-memory index footprint (including tombstone entries).

  - name: MemDataBytesWithTombs_ns
    description: Data bytes in memory for namespace <NS>, including tombstones
    command: asadm -cf "<bundle>" -e "show stat namespace <NS> like memory_data_bytes|data_used_bytes -flip"
    parse: |
      Let DATA = third character of StoragePattern_ns.

      If DATA == 'M':
        - Prefer "memory_data_bytes" for <NS> (sum across all nodes).
        - If 0/missing, fall back to "data_used_bytes" for in-memory namespaces.
        - MemDataBytesWithTombs_ns = sum of chosen metric across nodes.

      If DATA == 'D':
        - MemDataBytesWithTombs_ns = 0
          (data is on device; do not count record bodies as data memory).

      In pure planning mode (no collectinfo), you can approximate via:
        MemDataBytesWithTombs_ns ≈ (MasterObjectCount_ns * ReplicationFactor_ns)
                                   * AvgRecordSizeBytes_ns
        when DATA == 'M'; 0 when DATA == 'D'.

  - name: TombstonePct_ns
    description: Tombstones as a fraction of live master records for namespace <NS>
    command: asadm -cf "<bundle>" -e "show stat namespace <NS> like master_objects|master_tombstones -flip"
    parse: |
      MasterObjects_total    = sum of "master_objects" across nodes for <NS>.
      MasterTombstones_total = sum of "master_tombstones" across nodes for <NS>.

      If MasterObjects_total > 0:
        TombstonePct_ns = MasterTombstones_total / MasterObjects_total
      Else:
        TombstonePct_ns = 0.0


