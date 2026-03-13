#!/usr/bin/env bash
#
# gather_asadm_for_calculations.sh
#
# Runs asadm commands needed to fix/verify capacity calculation derivations.
# Output is labeled so it can be uploaded for analysis.
#
# Usage:
#   ./scripts/gather_asadm_for_calculations.sh <collectinfo_bundle>
#
# Example:
#   ./scripts/gather_asadm_for_calculations.sh nielsen-collect_info_v6x.tar
#   ./scripts/gather_asadm_for_calculations.sh bundle.zip > asadm_output.txt
#

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <collectinfo_bundle> [output_file]" >&2
  echo "  collectinfo_bundle: path to .zip, .tgz, or .tar" >&2
  echo "  output_file: optional; if omitted, prints to stdout" >&2
  exit 1
fi

BUNDLE="$1"
OUTPUT="${2:-}"

if [[ ! -f "$BUNDLE" ]]; then
  echo "ERROR: Bundle not found: $BUNDLE" >&2
  exit 1
fi

if ! command -v asadm >/dev/null 2>&1; then
  echo "ERROR: asadm not found in PATH" >&2
  exit 1
fi

run_asadm() {
  asadm -cf "$BUNDLE" -e "$1" 2>/dev/null || true
}

section() {
  echo ""
  echo "############################################"
  echo "# $1"
  echo "############################################"
  echo ""
}

cmd_section() {
  echo "--- COMMAND: $1 ---"
  run_asadm "$1"
  echo ""
}

# Redirect to file if requested
if [[ -n "$OUTPUT" ]]; then
  exec >"$OUTPUT"
fi

echo "=== asadm output for capacity calculation derivations ==="
echo "Bundle: $BUNDLE"
echo "Date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"

###############################################################################
# 1. Cluster summary (Device Total, Devices Total, Cluster Size, Memory, etc.)
###############################################################################
section "1. CLUSTER SUMMARY"
cmd_section "summary"

###############################################################################
# 2. Discover namespaces
###############################################################################
section "2. NAMESPACES IN BUNDLE"
cmd_section "show config namespace -flip"

# Parse namespace names for per-namespace commands
NAMESPACES=()
while read -r line; do
  clean="${line//\~/ }"
  clean="$(echo "$clean" | sed 's/^[[:space:]]*//')"
  if [[ "$clean" == *"Namespace Configuration"* ]]; then
    ns="${clean%% *}"
    [[ -n "$ns" ]] && NAMESPACES+=("$ns")
  fi
done < <(run_asadm "show config namespace -flip")

if [[ ${#NAMESPACES[@]} -gt 0 ]]; then
  NAMESPACES=($(printf '%s\n' "${NAMESPACES[@]}" | sort -u))
fi

if [[ ${#NAMESPACES[@]} -eq 0 ]]; then
  echo "No namespaces found; per-namespace sections will be skipped."
  NAMESPACES=(locks users_eu)
fi

echo "Discovered namespaces: ${NAMESPACES[*]}"

###############################################################################
# 3. Per-namespace: config (storage pattern, thresholds)
###############################################################################
section "3. PER-NAMESPACE CONFIG (storage-engine, index-type, sindex-type)"
for NS in "${NAMESPACES[@]}"; do
  echo "--- Namespace: $NS ---"
  cmd_section "show config namespace $NS -flip"
done

section "4. PER-NAMESPACE STORAGE THRESHOLDS (max-used-pct, min-avail-pct) [6.x]"
for NS in "${NAMESPACES[@]}"; do
  echo "--- Namespace: $NS ---"
  cmd_section "show config namespace $NS like max-used-pct -flip"
  cmd_section "show config namespace $NS like min-avail-pct -flip"
done

# 7.x stop-writes-used-pct (in case bundle is 7.x)
section "4b. PER-NAMESPACE STORAGE THRESHOLDS (stop-writes-used-pct) [7.x]"
for NS in "${NAMESPACES[@]}"; do
  echo "--- Namespace: $NS ---"
  cmd_section "show config namespace $NS like stop-writes-used-pct -flip"
done

###############################################################################
# 5. Per-namespace: master_objects (object count)
###############################################################################
section "5. PER-NAMESPACE MASTER OBJECTS"
for NS in "${NAMESPACES[@]}"; do
  echo "--- Namespace: $NS ---"
  cmd_section "show stat namespace $NS like master_objects -flip"
done

###############################################################################
# 6. Per-namespace: device/memory data bytes (AvgRecordSizeBytes derivation)
###############################################################################
section "6. PER-NAMESPACE DATA BYTES (device_data_bytes, memory_data_bytes, data_used_bytes)"
for NS in "${NAMESPACES[@]}"; do
  echo "--- Namespace: $NS ---"
  cmd_section "show stat namespace $NS like device_data_bytes|memory_data_bytes|data_used_bytes -flip"
done

###############################################################################
# 7. Device used (cluster-level check)
###############################################################################
section "7. PER-NAMESPACE DEVICE USED BYTES (device_used_bytes)"
for NS in "${NAMESPACES[@]}"; do
  echo "--- Namespace: $NS ---"
  cmd_section "show stat namespace $NS like device_used_bytes -flip"
done

###############################################################################
# 8. Memory: system stop-writes and per-namespace index/data bytes
###############################################################################
section "8. MEMORY CONFIG (stop-writes-sys-memory-pct)"
for NS in "${NAMESPACES[@]}"; do
  echo "--- Namespace: $NS ---"
  cmd_section "show config namespace $NS like stop-writes-sys-memory-pct -flip"
done

section "9. PER-NAMESPACE INDEX BYTES (IndexBytesWithTombs)"
for NS in "${NAMESPACES[@]}"; do
  echo "--- Namespace: $NS ---"
  cmd_section "show stat namespace $NS like index_used_bytes|sindex_used_bytes|set_index_used_bytes -flip"
done

###############################################################################
# 10. Tombstones (TombstonePct_ns)
###############################################################################
section "10. PER-NAMESPACE TOMBSTONES (master_objects, master_tombstones)"
for NS in "${NAMESPACES[@]}"; do
  echo "--- Namespace: $NS ---"
  cmd_section "show stat namespace $NS like master_objects|master_tombstones -flip"
done

###############################################################################
# 11. Replication factor (from config)
###############################################################################
section "11. PER-NAMESPACE REPLICATION FACTOR"
for NS in "${NAMESPACES[@]}"; do
  echo "--- Namespace: $NS ---"
  cmd_section "show config namespace $NS like replication-factor -flip"
done

echo ""
echo "=== END asadm output ==="
