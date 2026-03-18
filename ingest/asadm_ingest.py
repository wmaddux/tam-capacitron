"""
Collectinfo ingestion via asadm: run asadm -cf <bundle> -e "summary" (and optional
commands), parse output, and return a dict for the mapping layer.
Requires asadm on PATH. See docs/COLLECTINFO_INPUT_MAPPING.md.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


def run_asadm(bundle_path: str, command: str, timeout: int = 60) -> tuple[str | None, str | None]:
    """
    Run asadm in collectinfo-analyzer mode: asadm -cf <bundle_path> -e "<command>".
    Returns (stdout, stderr). Returns (None, error_message) on failure.
    """
    if not shutil.which("asadm"):
        return None, "asadm not found on PATH"
    path = str(Path(bundle_path).resolve())
    if not Path(path).is_file():
        return None, f"Bundle not found: {path}"
    try:
        result = subprocess.run(
            ["asadm", "-cf", path, "-e", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return None, result.stderr or result.stdout or f"asadm exited {result.returncode}"
        return result.stdout, None
    except FileNotFoundError:
        return None, "asadm not found on PATH"
    except subprocess.TimeoutExpired:
        return None, "asadm timed out"


def _parse_size(s: str) -> float:
    """Parse human sizes: 21.270 TB, 3.885 TB, 6.447 G, 1.000 M, 500 K. Returns numeric value."""
    s = (s or "").strip()
    if not s:
        return 0.0
    s = s.replace(",", "")
    m = re.match(r"^([\d.]+)\s*([KMGTP]?)\s*$", s, re.IGNORECASE)
    if not m:
        try:
            return float(s)
        except ValueError:
            return 0.0
    num = float(m.group(1))
    suffix = (m.group(2) or "").upper()
    if suffix == "K":
        return num * 1e3
    if suffix == "M":
        return num * 1e6
    if suffix == "G":
        return num * 1e9
    if suffix == "T":
        return num * 1e12
    if suffix == "P":
        return num * 1e15
    return num


def _parse_pct(s: str) -> float:
    """Parse percentage: '24.0 %' or '31.95 %' -> 0.24, 0.3195."""
    s = (s or "").strip().replace("%", "").strip()
    if not s:
        return 0.0
    try:
        v = float(s)
        if v > 1:
            return v / 100.0
        return v
    except ValueError:
        return 0.0


def _row_object_count(row: dict[str, str]) -> float:
    """Return object count for a namespace summary row. Uses Objects then Master (same key for selection and value)."""
    raw = row.get("Objects", row.get("Master", "")) or ""
    return _parse_size(raw)


def _cluster_summary_table(lines: list[str]) -> dict[str, str]:
    """Extract key|value pairs from Cluster Summary section (pipe-delimited)."""
    out = {}
    for line in lines:
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2 and parts[0] and not parts[0].startswith("~"):
            key = re.sub(r"\s+", " ", parts[0])
            out[key] = parts[1]
    return out


def _namespace_summary_rows(lines: list[str]) -> list[dict[str, str]]:
    """
    Parse Namespace Summary table: find header row (first line with Namespace;
    often followed by a subheader with Total, Per-Node, Factors, Read%, Objects).
    Use the line with more columns as header so data rows align.
    """
    rows = []
    header = None
    seen_namespace_line = False
    for line in lines:
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if not parts:
            continue
        if "Namespace" in (parts[0] or "") and "Drives" in " ".join(parts):
            seen_namespace_line = True
            header = [re.sub(r"\s+", " ", p) or f"col_{i}" for i, p in enumerate(parts)]
            continue
        if seen_namespace_line and header is not None:
            # Next line may be subheader (Total, Per-Node, Factors, Read%, Objects) with more columns
            if len(parts) > len(header) and ("Factors" in " ".join(parts) or "Read%" in " ".join(parts) or "Objects" in " ".join(parts)):
                header = [re.sub(r"\s+", " ", p) or f"col_{i}" for i, p in enumerate(parts)]
                if not header[0]:
                    header[0] = "Namespace"
                continue
            first = (parts[0] or "").strip()
            if first and not first.isdigit() and not first.startswith("col_") and "~" not in first:
                row = {}
                for i, h in enumerate(header):
                    if i < len(parts) and h and "~" not in (h or ""):
                        row[h] = parts[i].strip()
                if row:
                    rows.append(row)
    return rows


def parse_summary_output(raw: str, namespace: str | None = None) -> dict:
    """
    Parse asadm summary text output. Returns a dict with keys expected by
    ingestor_output_to_capacity_inputs (nodes_per_cluster, devices_per_node,
    device_size_gb, replication_factor, object_count, read_pct, write_pct, etc.).
    If namespace is set, use that namespace row; else use first data row (or largest by Master).
    """
    out: dict = {}
    if not raw or not raw.strip():
        return out
    lines = raw.splitlines()
    in_cluster = False
    in_ns = False
    cluster_lines: list[str] = []
    ns_lines: list[str] = []
    for line in lines:
        if "Cluster Summary" in line or "~~~~~~~~~~Cluster Summary" in line:
            in_cluster = True
            in_ns = False
            continue
        if "Namespace Summary" in line or "~~~~~~~~~~Namespace Summary" in line:
            in_cluster = False
            in_ns = True
            continue
        if in_cluster:
            if "Number of rows" in line or ("~~~" in line and "Cluster" not in line):
                in_cluster = False
            else:
                cluster_lines.append(line)
        if in_ns:
            if "Number of rows" in line:
                in_ns = False
            else:
                ns_lines.append(line)
    cs = _cluster_summary_table(cluster_lines)
    ns_rows = _namespace_summary_rows(ns_lines)
    if not ns_rows:
        ns_rows = []
    # Cluster fields
    cluster_size = cs.get("Cluster Size")
    if cluster_size:
        try:
            out["nodes_per_cluster"] = float(cluster_size.strip())
        except ValueError:
            pass
    devices_total = cs.get("Devices Total")
    devices_per_node = cs.get("Devices Per-Node")
    if devices_per_node:
        try:
            out["devices_per_node"] = float(devices_per_node.strip())
        except ValueError:
            pass
    device_total_s = cs.get("Device Total")
    if device_total_s and devices_total:
        try:
            num = float(re.sub(r"[^\d.]", "", device_total_s))
            dev_total = float(devices_total.strip())
            if dev_total > 0 and num > 0:
                # Summary may be "128.906 TB" or "21.270 GB"
                s_upper = (device_total_s or "").upper()
                total_gb = (num * 1024) if "TB" in s_upper else num
                out["device_size_gb"] = total_gb / dev_total
        except (ValueError, TypeError, ZeroDivisionError):
            pass
    device_used_s = cs.get("Device Used")
    if device_used_s:
        used_tb = _parse_size(device_used_s.replace("TB", "T").replace("GB", "G"))
        if used_tb > 0 and used_tb < 1e6:
            out["data_used_bytes"] = used_tb * (1024**4)
    if "data_used_bytes" not in out and device_used_s:
        try:
            used_tb = float(re.sub(r"[^\d.]", "", device_used_s))
            out["data_used_bytes"] = used_tb * (1024**4)
        except (ValueError, TypeError):
            pass
    out["nodes_lost"] = 0.0
    out["overhead_pct"] = 0.15
    out.setdefault("available_memory_gb", 64.0)
    if not ns_rows:
        return out
    row = None
    if namespace:
        for r in ns_rows:
            if r.get("Namespace") == namespace:
                row = r
                break
    if row is None:
        row = max(ns_rows, key=_row_object_count)
    ns_name = row.get("Namespace", "")
    repl = row.get("Replication Factors", row.get("Replication", row.get("Factors", "")))
    if repl:
        try:
            out["replication_factor"] = float(repl.strip())
        except ValueError:
            pass
    obj_count = _row_object_count(row)
    if obj_count > 0:
        out["object_count"] = obj_count
    cache_read = row.get("Cache Read%", row.get("Cache Read", row.get("Read%", "")))
    if cache_read:
        pct = _parse_pct(cache_read)
        if 0 <= pct <= 1:
            out["read_pct"] = pct
            out["write_pct"] = 1.0 - pct
    device_total_ns = row.get("Device Total", row.get("Total", ""))
    drives_total = row.get("Drives Total", row.get("Total", ""))
    if device_total_ns and drives_total and "device_size_gb" not in out:
        try:
            dt = _parse_size(device_total_ns.replace("TB", "T").replace("GB", "G"))
            if dt > 1e12:
                dt_gb = dt / (1024**3)
            else:
                dt_gb = dt / 1024 if "T" in (device_total_ns or "").upper() else dt
            dr = float(re.sub(r"[^\d.]", "", drives_total))
            if dr > 0:
                out["device_size_gb"] = dt_gb / dr
        except (ValueError, TypeError, ZeroDivisionError):
            pass
    return out


def _build_cluster_dict_from_summary(cs: dict) -> dict:
    """Build cluster-level dict from cluster summary table."""
    out: dict = {}
    cluster_name = cs.get("Cluster Name")
    if cluster_name is not None and str(cluster_name).strip():
        out["cluster_name"] = str(cluster_name).strip()
    cluster_size = cs.get("Cluster Size")
    if cluster_size:
        try:
            out["nodes_per_cluster"] = float(cluster_size.strip())
        except ValueError:
            pass
    devices_total = cs.get("Devices Total")
    devices_per_node = cs.get("Devices Per-Node")
    if devices_per_node:
        try:
            out["devices_per_node"] = float(devices_per_node.strip())
        except ValueError:
            pass
    device_total_s = cs.get("Device Total")
    if device_total_s and devices_total:
        try:
            num = float(re.sub(r"[^\d.]", "", device_total_s))
            dev_total = float(devices_total.strip())
            if dev_total > 0 and num > 0:
                s_upper = (device_total_s or "").upper()
                total_gb = (num * 1024) if "TB" in s_upper else num
                out["device_size_gb"] = total_gb / dev_total
        except (ValueError, TypeError, ZeroDivisionError):
            pass
    device_used_s = cs.get("Device Used")
    if device_used_s:
        used_tb = _parse_size(device_used_s.replace("TB", "T").replace("GB", "G"))
        if used_tb > 0 and used_tb < 1e6:
            out["data_used_bytes"] = used_tb * (1024**4)
    if "data_used_bytes" not in out and device_used_s:
        try:
            used_tb = float(re.sub(r"[^\d.]", "", device_used_s))
            out["data_used_bytes"] = used_tb * (1024**4)
        except (ValueError, TypeError):
            pass
    out["nodes_lost"] = 0.0
    out["overhead_pct"] = 0.15
    # Memory (Data + Indexes) Total or Memory Total (TB/GB) -> available_memory_gb per node
    # (Absent in 7.1/7.2 summary; caller should use _available_memory_gb_from_system_free_mem.)
    nodes = out.get("nodes_per_cluster")
    for key, val in cs.items():
        if val and "Memory" in key and "Total" in key and "Used" not in key:
            try:
                num = float(re.sub(r"[^\d.]", "", val))
                s_upper = (val or "").upper()
                total_gb = (num * 1024) if "TB" in s_upper else num
                if total_gb > 0 and nodes and nodes > 0:
                    out["available_memory_gb"] = total_gb / nodes
            except (ValueError, TypeError):
                pass
            break
    return out


def _row_namespace_name(row: dict[str, str]) -> str:
    """Get namespace name from a summary row; header may be 'Namespace' or ' Namespace'."""
    for k, v in row.items():
        if k and "namespace" in k.lower() and (v or "").strip():
            return (v or "").strip()
    return (list(row.values())[0] or "").strip() if row else ""


def _row_to_namespace_dict(row: dict[str, str], cluster_device_size_gb: float | None) -> dict:
    """Build one namespace workload dict from a namespace summary row."""
    ns_name = _row_namespace_name(row)
    repl = row.get("Replication Factors", row.get("Replication", row.get("Factors", "")))
    replication_factor = 2.0
    if repl:
        try:
            replication_factor = float(repl.strip())
        except ValueError:
            pass
    obj_count = _row_object_count(row)
    read_pct = 0.5
    write_pct = 0.5
    cache_read = row.get("Cache Read%", row.get("Cache Read", row.get("Read%", "")))
    if cache_read:
        pct = _parse_pct(cache_read)
        if 0 <= pct <= 1:
            read_pct = pct
            write_pct = 1.0 - pct
    device_size_gb = cluster_device_size_gb
    device_total_ns = row.get("Device Total", row.get("Total", ""))
    drives_total = row.get("Drives Total", row.get("Total", ""))
    if device_total_ns and drives_total:
        try:
            dt = _parse_size(device_total_ns.replace("TB", "T").replace("GB", "G"))
            if dt > 1e12:
                dt_gb = dt / (1024**3)
            else:
                dt_gb = dt / 1024 if "T" in (device_total_ns or "").upper() else dt
            dr = float(re.sub(r"[^\d.]", "", drives_total))
            if dr > 0:
                device_size_gb = dt_gb / dr
        except (ValueError, TypeError, ZeroDivisionError):
            pass
    # Drives Total from namespace row: 0 = in-memory only (no device data)
    drives_total_val = 0.0
    try:
        dr = row.get("Drives Total", row.get("Total", ""))
        if dr:
            drives_total_val = float(re.sub(r"[^\d.]", "", dr))
    except (ValueError, TypeError):
        pass
    d: dict = {
        "name": ns_name,
        "replication_factor": replication_factor,
        "object_count": obj_count,
        "read_pct": read_pct,
        "write_pct": write_pct,
        "tombstone_pct": 0.0,
        "si_count": 0.0,
        "si_entries_per_object": 0.0,
        "drives_total": drives_total_val,
    }
    if device_size_gb is not None:
        d["device_size_gb"] = device_size_gb
    return d


def parse_summary_output_multi(raw: str) -> dict:
    """
    Parse asadm summary text and return cluster-level dict + list of namespace dicts.
    Returns { "cluster": {...}, "namespaces": [ {...}, ... ] } for the mapping layer.
    Cluster has: nodes_per_cluster, devices_per_node, device_size_gb, available_memory_gb,
    overhead_pct, nodes_lost, data_used_bytes (optional).
    Each namespace has: name, replication_factor, object_count, read_pct, write_pct,
    tombstone_pct, si_count, si_entries_per_object, and optionally device_size_gb.
    """
    result: dict = {"cluster": {}, "namespaces": []}
    if not raw or not raw.strip():
        return result
    lines = raw.splitlines()
    in_cluster = False
    in_ns = False
    cluster_lines = []
    ns_lines = []
    for line in lines:
        if "Cluster Summary" in line or "~~~~~~~~~~Cluster Summary" in line:
            in_cluster = True
            in_ns = False
            continue
        if "Namespace Summary" in line or "~~~~~~~~~~Namespace Summary" in line:
            in_cluster = False
            in_ns = True
            continue
        if in_cluster:
            if "Number of rows" in line or ("~~~" in line and "Cluster" not in line):
                in_cluster = False
            else:
                cluster_lines.append(line)
        if in_ns:
            if "Number of rows" in line:
                in_ns = False
            else:
                ns_lines.append(line)
    cs = _cluster_summary_table(cluster_lines)
    result["cluster"] = _build_cluster_dict_from_summary(cs)
    ns_rows = _namespace_summary_rows(ns_lines)
    cluster_device_gb = result["cluster"].get("device_size_gb")
    for row in ns_rows:
        result["namespaces"].append(_row_to_namespace_dict(row, cluster_device_gb))
    return result


def _available_memory_gb_from_system_free_mem(bundle_path: str) -> float | None:
    """
    Derive available memory per node (GB) from system_free_mem stats when summary has no
    Memory Total (e.g. Aerospike 7.1/7.2 summary only shows Shmem Index Used).
    For each node: total_mem_kB = system_free_mem_kbytes / (system_free_mem_pct / 100).
    Returns mean(total_mem_kB) / 1024 / 1024 as GB per node for the cluster, or None if
    stats are missing or parse fails.
    """
    stdout, err = run_asadm(
        bundle_path,
        "show statistics like system_free_mem -flip",
    )
    if err or not stdout:
        return None
    totals_kb: list[float] = []
    for line in (stdout or "").splitlines():
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        free_kb_s = parts[1].replace(" ", "")
        pct_s = parts[2].replace(" ", "").replace("%", "")
        if not free_kb_s.replace(".", "").replace("-", "").isdigit():
            continue
        if not pct_s.replace(".", "").replace("-", "").isdigit():
            continue
        try:
            free_kb = float(free_kb_s)
            pct = float(pct_s)
            if pct <= 0 or pct > 100:
                continue
            total_kb = free_kb / (pct / 100.0)
            totals_kb.append(total_kb)
        except ValueError:
            continue
    if not totals_kb:
        return None
    mean_kb = sum(totals_kb) / len(totals_kb)
    return mean_kb / (1024.0 * 1024.0)


def _sum_stat_column(raw: str) -> float:
    """
    Parse asadm flipped stat output (e.g. show stat namespace X like device_used_bytes -flip).
    Sum the numeric values in the second column (one per node). Returns 0 if parse fails.
    """
    total = 0.0
    for line in (raw or "").splitlines():
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        # Skip header (e.g. "Node" or "device_used_bytes")
        val_s = parts[1].replace(" ", "")
        if not val_s or not val_s.replace(".", "").replace("-", "").isdigit():
            continue
        try:
            total += float(val_s)
        except ValueError:
            continue
    return total


def _namespace_device_data_bytes(bundle_path: str, namespace_name: str) -> float | None:
    """
    Get total device data/used bytes for a namespace via asadm (for storage derivation).
    Tries device_data_bytes first, then device_used_bytes (per model_calculation_storage_util).
    Returns None if asadm fails or both stats are missing/zero.
    """
    for stat_name in ("device_data_bytes", "device_used_bytes"):
        stdout, err = run_asadm(
            bundle_path,
            f'show stat namespace {namespace_name!r} like {stat_name} -flip',
        )
        if err or not stdout:
            continue
        total = _sum_stat_column(stdout)
        if total > 0:
            return total
    return None


def asadm_summary_to_capacity_dict(bundle_path: str, namespace: str | None = None) -> dict:
    """
    Run asadm -cf bundle_path -e "summary", parse output, and return dict for mapping layer.
    If asadm is missing or fails, returns empty dict (caller should fall back to stub).
    """
    stdout, err = run_asadm(bundle_path, "summary")
    if err or not stdout:
        return {}
    ns = namespace
    if ns is None:
        ns = (os.environ.get("CAPACITRON_NAMESPACE") or "").strip() or None
    return parse_summary_output(stdout, namespace=ns)


def asadm_summary_to_capacity_multi(bundle_path: str) -> dict:
    """
    Run asadm -cf bundle_path -e "summary", parse output, and return cluster + namespaces.
    Enriches each namespace with data_used_bytes from show stat (device_data_bytes or
    device_used_bytes) per docs/model_calculation_storage_util.md so Data stored matches
    Device Used when loading from collectinfo.
    Returns { "cluster": {...}, "namespaces": [ {...}, ... ] }. If asadm is missing or
    fails, returns empty cluster and empty namespaces (caller should fall back to stub).
    """
    stdout, err = run_asadm(bundle_path, "summary")
    if err or not stdout:
        return {"cluster": {}, "namespaces": []}
    result = parse_summary_output_multi(stdout)
    # When summary has no Memory Total (e.g. 7.1/7.2), derive from system_free_mem per node
    if result.get("cluster") is not None and "available_memory_gb" not in result["cluster"]:
        gb = _available_memory_gb_from_system_free_mem(bundle_path)
        if gb is not None and gb > 0:
            result["cluster"]["available_memory_gb"] = gb
    for ns_dict in result.get("namespaces") or []:
        name = (ns_dict.get("name") or "").strip()
        if not name:
            continue
        device_bytes = _namespace_device_data_bytes(bundle_path, name)
        if device_bytes is not None and device_bytes > 0:
            ns_dict["data_used_bytes"] = device_bytes
    return result
