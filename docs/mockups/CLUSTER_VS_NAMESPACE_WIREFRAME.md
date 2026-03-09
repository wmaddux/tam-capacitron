# Cluster vs namespace parameter wireframe

This document and the companion HTML mockup **[mockup-cluster-namespace-split-with-definition.html](mockup-cluster-namespace-split-with-definition.html)** separate input parameters into **cluster-wide** (one value for the whole cluster) and **namespace-specific** (per namespace, or per "use case" in the sizing estimator). It is based on the chosen project wireframe mockup-cluster-namespace-split-with-definition.html and [STRAWMAN_UI_AND_FLOW.md](../STRAWMAN_UI_AND_FLOW.md).

## Parameter classification

The **Workload** sheet in **Tool_Aerospike_Sizing_Estimator_(10_14).xlsx** defines parameters per use case (columns C–G = use case 1–5). Each use case corresponds to a namespace (or set). See [CALCULATION_CATALOG.md](../CALCULATION_CATALOG.md) for the full mapping.

### Cluster-wide (one value for the whole cluster)

| Parameter | Description | Current section |
|-----------|-------------|-----------------|
| Nodes per cluster | Total nodes | Topology |
| Devices per node | Storage devices per node | Topology |
| Device size (GB) | Capacity per device | Topology |
| Available memory per node (GB) | RAM per node for Aerospike | Server / memory |
| Overhead % | Memory reserved for overhead | Server / memory |
| Nodes lost (failure) | Nodes lost in failure scenario | Resilience |

### Namespace-specific (per namespace / per use case in Workload sheet)

| Parameter | Description | Workload sheet reference |
|-----------|-------------|--------------------------|
| Replication factor | Copies per record | RF_1 … RF_5 (C7–G7) |
| Master object count | Object count | ObjCount1…5 (C10–G10) |
| Avg record size (bytes) | Average object size | AvgObjSize1…5 (C9–G9) |
| Read % / Write % | Read/write mix | Avg/Peak RPS/WPS (C21–G25) |
| Tombstone % | Fraction of tombstones | (in our model) |
| SI count | Number of secondary indexes | NumberOfSIs1…5 (C15–G15) |
| SI entries per object | SI coverage | SICoverage1…5 (C16–G16) |

Additional namespace-level parameters in the full Workload sheet (for future phases): objects per record, compression reduction, peak RPS/WPS, PI/SI storage (Ram or Disk), cached levels of SI on disk B-tree.

## Wireframe layout

The mockup [mockup-cluster-namespace-split-with-definition.html](mockup-cluster-namespace-split-with-definition.html) shows:

1. **Cluster** – One section containing:
   - **Topology:** Nodes per cluster, Devices per node, Device size (GB)
   - **Server / memory:** Available memory per node (GB), Overhead %
   - **Resilience:** Nodes lost (failure)

2. **Namespace (workload)** – One section containing:
   - **Active namespace:** A single dropdown or selector (e.g. "Namespace: wi-pzn") when loading from collectinfo; placeholder for future "Add namespace" when we support multiple.
   - **Workload:** Replication factor, Master object count, Avg record size (bytes), Read %, Write %, Tombstone %, SI count, SI entries per object.

3. **Definition column:** A third column (no card header in the mockup, just the help content). Clicking a parameter label in the Inputs or Outputs column displays that parameter's definition/help in this column.

4. **Note for future:** A short line such as "Multiple namespaces: coming later" or "Add namespace" to indicate that the UI will later support multiple namespaces, each with its own workload parameters (e.g. one card or section per namespace).

## Implementation note

Implementation of multi-namespace (engine, API shape, load-from-collectinfo returning multiple namespaces) is out of scope for this wireframe. The deliverable is the layout and parameter grouping so the product can agree on structure before implementation. When implementing multi-namespace, the engine and API should follow the aggregation approach described in [PLAN.md](../PLAN.md) (and CALCULATION_CATALOG Sizing Estimator).
