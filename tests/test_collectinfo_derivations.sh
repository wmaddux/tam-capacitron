#!/usr/bin/env bash
#
# test_derivations_all_ns.sh
#
# Usage:
#   ./test_derivations_all_ns.sh <collectinfo_bundle.tgz>
#
# This script tests the Storage/Memory derivations for ALL namespaces
# found in a collectinfo bundle, using asadm -cf in offline mode.
#

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <collectinfo_bundle.tgz>" >&2
  exit 1
fi

BUNDLE="$1"

if ! command -v asadm >/dev/null 2>&1; then
  echo "ERROR: asadm not found in PATH" >&2
  exit 1
fi

echo "=== Using bundle: $BUNDLE"
echo

###############################################################################
# Helpers
###############################################################################

run_asadm() {
  local cmd="$1"
  # Suppress stderr noise from asadm (Config_file, Broken pipe, etc.)
  asadm -cf "$BUNDLE" -e "$cmd" 2>/dev/null
}

sum_column_values() {
  # Reads from stdin (flipped table)
  awk -F'|' '
    NR == 1 { next }                  # skip header
    $1 ~ /:/ {
      gsub(/ /, "", $2);
      if ($2 ~ /^[0-9.]+$/) total += $2
    }
    END { printf "%.0f\n", total }'
}

extract_single_value() {
  # Reads from stdin (flipped table)
  awk -F'|' '
    NR == 1 { next }                  # skip header
    $1 ~ /:/ {
      gsub(/ /, "", $2);
      print $2;
      exit
    }'
}

###############################################################################
# Cluster-level: from summary
###############################################################################

echo "=== Cluster-level summary ==="

SUMMARY_OUT="$(run_asadm "summary" || true)"

NodesPerCluster="$(
  awk '
    /^Cluster Size/ {
      gsub(/\|/, "");
      print $NF
    }' <<< "$SUMMARY_OUT"
)"
echo "NodesPerCluster = ${NodesPerCluster:-N/A}"

DevicesPerNode="$(
  awk '
    /^Devices Per-Node/ {
      gsub(/\|/, "");
      print $NF
    }' <<< "$SUMMARY_OUT"
)"
echo "DevicesPerNode  = ${DevicesPerNode:-N/A}"

# Device Total may be in TB or GB; convert to GB for DeviceTotalGB_cluster
DeviceTotal_raw="$(
  awk '
    /^Device Total/ {
      gsub(/\|/, "");
      # Second-to-last field is typically the number, last may be unit (TB/GB)
      line = $0
      gsub(/\|/, " ", line)
      sub(/^[[:space:]]+/, "", line)
      sub(/[[:space:]]+$/, "", line)
      n = split(line, a, /[[:space:]]+/)
      if (n >= 1) {
        num = a[n-1]+0
        unit = (n >= 2 ? a[n] : "")
        if (unit ~ /TB/) print num * 1024
        else if (unit ~ /GB/) print num
        else print num
      }
    }' <<< "$SUMMARY_OUT"
)"
DeviceTotalGB_cluster="$DeviceTotal_raw"
echo "DeviceTotalGB_cluster = ${DeviceTotalGB_cluster:-N/A}"

if [[ -n "${DeviceTotalGB_cluster}" && -n "${NodesPerCluster}" && -n "${DevicesPerNode}" ]]; then
  DeviceSizeGB="$(awk -v dt="$DeviceTotalGB_cluster" -v n="$NodesPerCluster" -v d="$DevicesPerNode" \
    'BEGIN { if (n*d>0) printf "%.6f\n", dt/(n*d); else print "0" }')"
else
  DeviceSizeGB="0"
fi
echo "DeviceSizeGB    = $DeviceSizeGB"

# Memory (Data + Indexes) Total or Memory Total (GB) - first matching line only
MemoryTotalGB_cluster="$(
  awk '
    /Memory.*Total/ && !/Used/ {
      gsub(/\|/, "");
      line = $0
      gsub(/\|/, " ", line)
      n = split(line, a, /[[:space:]]+/)
      if (n >= 2 && a[n-1]+0 > 0) {
        num = a[n-1]+0
        unit = (n >= 2 ? a[n] : "")
        if (unit ~ /TB/) print num * 1024
        else if (unit ~ /GB/) print num
        else print num
        exit
      }
    }' <<< "$SUMMARY_OUT"
)"
echo "MemoryTotalGB_cluster = ${MemoryTotalGB_cluster:-N/A}"

if [[ -n "${MemoryTotalGB_cluster}" && -n "${NodesPerCluster}" ]]; then
  MemoryTotalGB_per_node="$(awk -v mt="$MemoryTotalGB_cluster" -v n="$NodesPerCluster" \
    'BEGIN { if (n>0) printf "%.6f\n", mt/n; else print "0" }')"
else
  MemoryTotalGB_per_node="0"
fi
echo "MemoryTotalGB_per_node = $MemoryTotalGB_per_node"
echo

###############################################################################
# Discover namespaces from config (robust in collectinfo mode)
###############################################################################

echo "=== Discovering namespaces ==="

CONFIG_NS_OUT="$(run_asadm "show config namespace -flip" || true)"

NAMESPACES=()
while read -r line; do
  # Remove leading tildes and compress spaces
  clean="${line//\~/ }"
  clean="$(echo "$clean" | sed 's/^[[:space:]]*//')"
  # Match lines like: "test Namespace Configuration (2026-...)"
  if [[ "$clean" == *"Namespace Configuration"* ]]; then
    ns="${clean%% *}"
    [[ -n "$ns" ]] && NAMESPACES+=("$ns")
  fi
done <<< "$CONFIG_NS_OUT"

if [[ ${#NAMESPACES[@]} -gt 0 ]]; then
  NAMESPACES=($(printf "%s\n" "${NAMESPACES[@]}" | sort -u))
fi

if [[ ${#NAMESPACES[@]} -eq 0 ]]; then
  echo "No namespaces found in bundle; exiting." >&2
  exit 1
fi

echo "Found namespaces: ${NAMESPACES[*]}"
echo

###############################################################################
# Loop over namespaces and test derivations
###############################################################################

for NS in "${NAMESPACES[@]}"; do
  echo "==================================================================="
  echo "Namespace: $NS"
  echo "==================================================================="

  ###########################################################################
  # Cluster-level thresholds per-namespace (storage + memory)
  ###########################################################################

  StopWritesStoragePct="$(
    run_asadm "show config namespace $NS like stop-writes-used-pct -flip" \
      | extract_single_value || echo ""
  )"
  if [[ -z "$StopWritesStoragePct" ]]; then
    StopWritesStoragePct="$(
      run_asadm "show config namespace $NS like max-used-pct -flip" \
        | extract_single_value || echo "0"
    )"
  fi

  MinAvailStoragePct="$(
    run_asadm "show config namespace $NS like min-avail-pct -flip" \
      | extract_single_value || echo ""
  )"
  # Treat missing as 0
  if [[ -z "$MinAvailStoragePct" ]]; then
    MinAvailStoragePct="0"
  fi

  StopWritesSysMemoryPct="$(
    run_asadm "show config namespace $NS like stop-writes-sys-memory-pct -flip" \
      | extract_single_value || echo "0"
  )"

  echo "[CFG] StopWritesStoragePct   = $StopWritesStoragePct"
  echo "[CFG] MinAvailStoragePct     = $MinAvailStoragePct"
  echo "[CFG] StopWritesSysMemoryPct = $StopWritesSysMemoryPct"
  echo

  ###########################################################################
  # StoragePattern_ns
  ###########################################################################

  IndexType="$(
    run_asadm "show config namespace $NS like index-type -flip" \
      | extract_single_value || echo "shmem"
  )"
  SindexType="$(
    run_asadm "show config namespace $NS like sindex-type -flip" \
      | extract_single_value || echo "shmem"
  )"
  StorageEngine="$(
    run_asadm "show config namespace $NS like storage-engine -flip" \
      | extract_single_value || echo "device"
  )"

  case "$IndexType" in
    flash) PI="D" ;;
    *)     PI="M" ;;
  esac

  case "$SindexType" in
    flash) SI="D" ;;
    *)     SI="M" ;;
  esac

  # For MEMORY utilization semantics, DATA='M' when storage-engine is memory
  case "$StorageEngine" in
    memory) DATA="M" ;;
    device|pmem) DATA="D" ;;
    *) DATA="D" ;;
  esac

  StoragePattern_ns="${PI}${SI}${DATA}"

  echo "[PAT] IndexType         = $IndexType"
  echo "[PAT] SindexType        = $SindexType"
  echo "[PAT] StorageEngine     = $StorageEngine"
  echo "[PAT] StoragePattern_ns = $StoragePattern_ns"
  echo

  ###########################################################################
  # ReplicationFactor_ns, MasterObjectCount_ns
  ###########################################################################

  ReplicationFactor_ns="$(
    run_asadm "show config namespace $NS like replication-factor -flip" \
      | extract_single_value || echo "0"
  )"
  MasterObjectCount_ns="$(
    run_asadm "show stat namespace $NS like master_objects -flip" \
      | sum_column_values || echo "0"
  )"

  echo "[OBJ] ReplicationFactor_ns = $ReplicationFactor_ns"
  echo "[OBJ] MasterObjectCount_ns = $MasterObjectCount_ns"
  echo

  ###########################################################################
  # AvgRecordSizeBytes_ns, CompressionSavingsPct_ns (storage model)
  ###########################################################################

  dev_bytes="$(
    run_asadm "show stat namespace $NS like device_data_bytes -flip" \
      | sum_column_values || echo "0"
  )"
  device_used_bytes="$(
    run_asadm "show stat namespace $NS like device_used_bytes -flip" \
      | sum_column_values || echo "0"
  )"
  mem_bytes="$(
    run_asadm "show stat namespace $NS like memory_data_bytes -flip" \
      | sum_column_values || echo "0"
  )"
  used_bytes="$(
    run_asadm "show stat namespace $NS like data_used_bytes -flip" \
      | sum_column_values || echo "0"
  )"

  TotalDataBytes_ns=0
  SourceDataBytes="N/A"

  if [[ "$dev_bytes" != "0" ]]; then
    TotalDataBytes_ns="$dev_bytes"
    SourceDataBytes="device_data_bytes"
  elif [[ "$device_used_bytes" != "0" ]]; then
    TotalDataBytes_ns="$device_used_bytes"
    SourceDataBytes="device_used_bytes"
  elif [[ "$mem_bytes" != "0" ]]; then
    TotalDataBytes_ns="$mem_bytes"
    SourceDataBytes="memory_data_bytes"
  else
    TotalDataBytes_ns="$used_bytes"
    SourceDataBytes="data_used_bytes"
  fi

  # For planning, treat live objects as master_objects
  LiveObjects_ns="$MasterObjectCount_ns"

  if [[ "$LiveObjects_ns" != "0" ]]; then
    AvgRecordSizeBytes_ns="$(awk -v tb="$TotalDataBytes_ns" -v lo="$LiveObjects_ns" \
      'BEGIN { printf "%.2f\n", tb/lo }')"
  else
    AvgRecordSizeBytes_ns="0"
  fi

  echo "[SIZE] TotalDataBytes_ns ($SourceDataBytes) = $TotalDataBytes_ns"
  echo "[SIZE] LiveObjects_ns                      = $LiveObjects_ns"
  echo "[SIZE] AvgRecordSizeBytes_ns               = $AvgRecordSizeBytes_ns"

  CompressionRatio_ns="$(
    run_asadm "show stat namespace $NS like compression_ratio -flip" \
      | awk -F'|' '
          NR == 1 { next }
          $1 ~ /:/ {
            gsub(/ /, "", $2);
            if ($2 ~ /^[0-9.]+$/) { print $2; exit }
          }' || echo ""
  )"

  if [[ -z "$CompressionRatio_ns" ]]; then
    CompressionSavingsPct_ns="0.0"
  else
    CompressionSavingsPct_ns="$(awk -v r="$CompressionRatio_ns" \
      'BEGIN { printf "%.4f\n", 1-r }')"
  fi

  echo "[COMP] CompressionRatio_ns       = ${CompressionRatio_ns:-N/A}"
  echo "[COMP] CompressionSavingsPct_ns  = $CompressionSavingsPct_ns"
  echo

  ###########################################################################
  # TombstonePct_ns
  ###########################################################################

  MasterTombstones_total="$(
    run_asadm "show stat namespace $NS like master_tombstones -flip" \
      | sum_column_values || echo "0"
  )"

  if [[ "$MasterObjectCount_ns" != "0" ]]; then
    TombstonePct_ns="$(awk -v t="$MasterTombstones_total" -v m="$MasterObjectCount_ns" \
      'BEGIN { printf "%.6f\n", t/m }')"
  else
    TombstonePct_ns="0.0"
  fi

  echo "[TOMB] MasterTombstones_total = $MasterTombstones_total"
  echo "[TOMB] TombstonePct_ns        = $TombstonePct_ns"
  echo

  ###########################################################################
  # IndexBytesWithTombs_ns, MemDataBytesWithTombs_ns (for MemoryUtil)
  ###########################################################################

  idx_bytes="$(
    run_asadm "show stat namespace $NS like index_used_bytes -flip" \
      | sum_column_values || echo "0"
  )"
  sidx_bytes="$(
    run_asadm "show stat namespace $NS like sindex_used_bytes -flip" \
      | sum_column_values || echo "0"
  )"
  setidx_bytes="$(
    run_asadm "show stat namespace $NS like set_index_used_bytes -flip" \
      | sum_column_values || echo "0"
  )"

  IndexBytesWithTombs_ns="$(awk -v a="$idx_bytes" -v b="$sidx_bytes" -v c="$setidx_bytes" \
    'BEGIN { printf "%.0f\n", a+b+c }')"

  echo "[IDX] index_used_bytes_sum     = $idx_bytes"
  echo "[IDX] sindex_used_bytes_sum    = $sidx_bytes"
  echo "[IDX] set_index_used_bytes_sum = $setidx_bytes"
  echo "[IDX] IndexBytesWithTombs_ns   = $IndexBytesWithTombs_ns"

  DATA_CHAR="${StoragePattern_ns:2:1}"

  if [[ "$DATA_CHAR" == "M" ]]; then
    memdata_bytes="$(
      run_asadm "show stat namespace $NS like memory_data_bytes -flip" \
        | sum_column_values || echo "0"
    )"
    if [[ "$memdata_bytes" == "0" ]]; then
      memdata_bytes="$(
        run_asadm "show stat namespace $NS like data_used_bytes -flip" \
          | sum_column_values || echo "0"
      )"
    fi
    MemDataBytesWithTombs_ns="$memdata_bytes"
  else
    MemDataBytesWithTombs_ns="0"
  fi

  echo "[DATA] DATA char (3rd of StoragePattern_ns) = $DATA_CHAR"
  echo "[DATA] MemDataBytesWithTombs_ns            = $MemDataBytesWithTombs_ns"
  echo

done

echo "=== DONE: derivations tested for all namespaces ==="
