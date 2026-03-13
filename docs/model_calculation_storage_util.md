Pseudo-code for calculating Storage utilization %


# CONSTANT
BytesPerGB = 1024^3

############################################
# CLUSTER‑LEVEL INPUTS (AFFECT StorageUtil_%)
############################################

NodesPerCluster          # number of nodes in cluster
DevicesPerNode           # persistent devices per node used by Aerospike
DeviceSizeGB             # size of each device in GB
StorageOverheadPct       # fraction of raw device capacity reserved for FS/metadata/defrag
                         # e.g. 0.20 = 20%

StopWritesStoragePct     # "stop-writes at storage %" (max-used-pct or stop-writes-used-pct)
                         # e.g. 70 means stop-writes when 70% of data area is used

MinAvailStoragePct       # "min available storage %" (min-avail-pct)
                         # e.g. 10 means always keep 10% free

############################################
# NAMESPACE‑LEVEL INPUTS (AFFECT StorageUtil_%)
############################################

StoragePattern_ns        # 3-char PI/SI/DATA pattern, each char is 'M' or 'D'
                         #   MMM = PI in M,  SI in M,  DATA in M
                         #   MMD = PI in M,  SI in M,  DATA in D  (HMA)
                         #   DDD = PI in D,  SI in D,  DATA in D  (all-flash)
                         #   DMD = PI in D,  SI in M,  DATA in M  (no data on device)
                         #   CUSTOM = any other 3-char combination; DATA = 3rd char

ReplicationFactor_ns     # replication factor for namespace ns (RF)

MasterObjectCount_ns     # total master objects for namespace ns across the cluster

AvgRecordSizeBytes_ns    # average logical record size before compression
                         # (for capacity planning; see collectinfo notes)

CompressionSavingsPct_ns # fraction of space saved on device by compression (0–1)

TombstonePct_ns          # fraction of tombstones vs live master records
                         # tombstones ≈ TombstonePct_ns * live_records

############################################
# 1. CLUSTER USABLE DEVICE CAPACITY
############################################

RawDeviceGB_cluster =
    NodesPerCluster * DevicesPerNode * DeviceSizeGB

MaxDataPct =
    min( StopWritesStoragePct,
         100 - MinAvailStoragePct )

UsableDeviceGB_cluster =
    RawDeviceGB_cluster
      * (1 - StorageOverheadPct)
      * (MaxDataPct / 100.0)

############################################
# 2. PER‑NAMESPACE DEVICE DATA
############################################

# 2.1 Base logical data (live + tombstones, all replicas)

LiveRecs_ns =
    MasterObjectCount_ns * ReplicationFactor_ns

TotalRecs_ns =
    LiveRecs_ns * (1 + TombstonePct_ns)

EffectiveRecordSizeBytes_ns =
    AvgRecordSizeBytes_ns * (1 - CompressionSavingsPct_ns)

DataBytes_ns =
    TotalRecs_ns * EffectiveRecordSizeBytes_ns

DataGB_ns =
    DataBytes_ns / BytesPerGB

# 2.2 Map storage pattern → what fraction of DATA is on device

DataPlacement = third_character_of(StoragePattern_ns)  # 'M' or 'D'

if DataPlacement == 'D':
    DeviceDataGB_ns = DataGB_ns
else:
    DeviceDataGB_ns = 0

# 2.3 Sum across namespaces

TotalDeviceDataGB_all_ns =
    sum over all namespaces ns of DeviceDataGB_ns

############################################
# 3. FINAL STORAGE UTILIZATION %
############################################

StorageUtil_% =
    ( TotalDeviceDataGB_all_ns / UsableDeviceGB_cluster ) * 100





When deriving inputs from collectinfo, use the following methods (may differ between Aerospike versions)


cluster_inputs:
  - name: NodesPerCluster
    description: Number of nodes in the Aerospike cluster
    command: asadm -cf "<bundle>" -e "summary"
    parse: |
      Find the line starting with "Cluster Size".
      Example: "Cluster Size             18"
      NodesPerCluster = integer value on that line.

  - name: DevicesPerNode
    description: Number of Aerospike data devices per node
    command: asadm -cf "<bundle>" -e "summary"
    parse: |
      Find the line starting with "Devices Per-Node".
      Example: "Devices Per-Node         22"
      DevicesPerNode = integer value on that line.

  - name: DeviceSizeGB
    description: Size of each data device in GB
    command: asadm -cf "<bundle>" -e "summary"
    parse: |
      From the same summary output, find the line starting with "Device Total".
      Example: "Device Total             21.270 GB"
      DeviceTotalGB_cluster = numeric GB value on that line.

      Then:
        DeviceSizeGB = DeviceTotalGB_cluster / (NodesPerCluster * DevicesPerNode)

  - name: StorageOverheadPct
    description: Fraction of raw device capacity reserved for FS/metadata/defrag
    command: null
    parse: |
      Not present in collectinfo.
      Set manually for the planner, e.g. StorageOverheadPct = 0.20 (20%).

  - name: StopWritesStoragePct
    description: "Stop-writes at storage %" threshold
    command_v7_plus: asadm -cf "<bundle>" -e "show config namespace <NS> like stop-writes-used-pct -flip"
    command_pre_v7: asadm -cf "<bundle>" -e "show config namespace <NS> like max-used-pct -flip"
    parse: |
      For 7.x and later:
        parse "stop-writes-used-pct" for <NS>.
        StopWritesStoragePct = that numeric value.

      For pre-7:
        parse "max-used-pct" for <NS>.
        StopWritesStoragePct = that numeric value.

  - name: MinAvailStoragePct
    description: "Min available storage %" (min-avail-pct)
    command: asadm -cf "<bundle>" -e "show config namespace <NS> like min-avail-pct -flip"
    parse: |
      Parse "min-avail-pct" for <NS> as a numeric percentage.
      If it is missing/blank, treat MinAvailStoragePct = 0 (no explicit min-avail constraint).

namespace_inputs:
  - name: StoragePattern_ns
    description: 3-char PI/SI/DATA placement pattern (M or D for each) for STORAGE
    command: asadm -cf "<bundle>" -e "show config namespace <NS> -flip"
    parse: |
      From the namespace config for <NS>:

        1) Primary index (PI) → 1st char:
             if "index-type" == "flash" then PI = 'D'
             else PI = 'M'

        2) Secondary index (SI) → 2nd char:
             if "sindex-type" == "flash" then SI = 'D'
             else SI = 'M'

        3) Data placement (STORAGE semantics) → 3rd char:
             if storage-engine is "device { ... }" or "pmem { ... }" then DATA = 'D'
             if storage-engine is pure "memory { ... }" (no persistence) then DATA = 'M'

             For Aerospike 7 in-memory namespaces with storage-backed persistence
             (memory + persistence options):
               DATA = 'D' for StorageUtil_% because the unified format mirrors
               data to the persistence layer.

      StoragePattern_ns = PI + SI + DATA

  - name: ReplicationFactor_ns
    description: Namespace replication factor
    command: asadm -cf "<bundle>" -e "show config namespace <NS> like replication-factor -flip"
    parse: |
      Parse "replication-factor" for <NS> as integer.
      ReplicationFactor_ns = that value.

  - name: MasterObjectCount_ns
    description: Total master objects for this namespace across the cluster
    command: asadm -cf "<bundle>" -e "show stat namespace <NS> like master_objects -flip"
    parse: |
      Sum "master_objects" values across all nodes for <NS>.
      MasterObjectCount_ns = this sum.

  - name: AvgRecordSizeBytes_ns
    description: Average record size for planning (logical view)
    command: asadm -cf "<bundle>" -e "show stat namespace <NS> like device_data_bytes|memory_data_bytes|data_used_bytes|master_objects -flip"
    parse: |
      Choose data bytes source in this order:
        1) device_data_bytes (HMA / SSD / all-flash)
        2) memory_data_bytes (pure in-memory namespaces)
        3) data_used_bytes (fallback)

      Let TotalDataBytes_ns = sum of the chosen metric across all nodes.

      For the object count, use master objects:
        LiveObjects_ns = MasterObjectCount_ns

      If LiveObjects_ns > 0:
        AvgRecordSizeBytes_ns = TotalDataBytes_ns / LiveObjects_ns
      Else:
        AvgRecordSizeBytes_ns = 0

      Note:
        - When TotalDataBytes_ns comes from device_data_bytes and compression
          is enabled, this is the compressed size. Use this directly for
          "as-is" StorageUtil_% from collectinfo, and set
          CompressionSavingsPct_ns = 0 in the utilization calculation.

  - name: CompressionSavingsPct_ns
    description: Fraction of space saved on device by compression (0–1)
    command: asadm -cf "<bundle>" -e "show stat namespace <NS> like compression_ratio -flip"
    parse: |
      For live "as-is" StorageUtil_% from collectinfo:
        - Set CompressionSavingsPct_ns = 0.0
          (device_data_bytes is already compressed; do not apply savings again).

      For capacity planning using logical sizes:
        - Parse "device_compression_ratio" or "compression_ratio" for <NS>.
        - Let CompressionRatio_ns = that metric (compressed / logical).
        - Then you MAY set:
            CompressionSavingsPct_ns = 1 - CompressionRatio_ns
          and pair this with a logical AvgRecordSizeBytes_ns from modeling.

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


