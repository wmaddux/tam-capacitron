# Strawman: UI and process flow

Defined before implementing the full calculation engine so the UI contract stays stable and modular.

## Chosen wireframe

**The project wireframe is [docs/mockups/mockup-cluster-namespace-split-with-definition.html](../mockups/mockup-cluster-namespace-split-with-definition.html).** New UI work (e.g. updating `app/static/index.html`) should follow this mockup.

- **Theme:** Light (cool neutral): light grey page, white panels, dark text, blue accent.
- **Layout:** Three columns: **Inputs** | **Outputs** | **Definition**. Inputs column: **Cluster** card (title "Cluster (topology, server, resilience)") with cluster name (text input) and topology, server/memory, resilience parameters; **Namespaces (workload)** card with one sub-card per namespace (namespace name, Remove, workload params) and "+ Add namespace". Outputs column: same structure as before—**Healthy cluster** and **Failure** with section dividers; placeholders for **Data growth** and **Performance**. **Definition** column: no card chrome; shows parameter help text; clicking a parameter label in Inputs or Outputs displays that parameter's definition here.
- **Output cards:** Related metrics are grouped in one card per topic. Each card has a light grey background, border, and padding. Storage card: Storage utilization % (primary) + Data stored, Device total storage, Total available storage, Total device count. Memory card: Memory utilization (base) % (primary) + supporting memory metrics. Failure card: Failure storage %, Failure memory % (both primary) + Effective nodes and capacity details.
- **Primary vs secondary:** Inside each card, the main metric (e.g. utilization %) uses a larger, bolder value; supporting rows use normal size.

See [docs/mockups/OUTPUT_ORGANIZATION.md](mockups/OUTPUT_ORGANIZATION.md) for output grouping rationale.

## Process flow

1. **Open app** → User sees the capacity planning screen with all inputs at **default minimum values** and outputs already computed (no blank or invalid state).
2. **Adjust inputs** → User changes values via **sliders, knobs, or dropdowns** (no "Apply"); **outputs update immediately** so they can correlate input changes with output effects.
3. **Optional: Load from source** → User may click **Load from defaults** (reset to safe minimums), or later: **Load from collectinfo**, **Load server specs from instance type**, **Load from output file**. Each Load populates the same input form from that source.
4. **Export or save state** → User clicks **Export** to write all inputs and outputs to a standard output file (JSON) for storage/sharing. Later: save named state and open **Comparison** view.
5. **Compare (later)** → User selects two states (e.g. saved A vs saved B) and sees side-by-side inputs and outputs.

## Main screens (wireframe)

### Single main screen: Capacity planning

```
+---------------------------------------------------------------------------+
|  Aerospike Capacity Planner                     [Export] [Load...]        |
+---------------------------------------------------------------------------+
|  INPUTS                    |  OUTPUTS                  |  DEFINITION      |
|  ------------------------- |  ------------------------ |  (help on click) |
|  Cluster (topology,        |  Healthy cluster          |  Click a param   |
|   server, resilience)      |  • Storage utilization %  |  label to show   |
|  • Cluster name  [______]  |  • Data stored, etc.      |  its definition  |
|  • Nodes per cluster  [o-] |  • Memory utilization %   |  here.           |
|  • Devices per node   [o-] |  ------------------------ |                  |
|  • Device size (GB)   [o-] |  Failure scenario         |                  |
|  • Available mem/node [o-] |  • Storage %, Memory %    |                  |
|  • Overhead %         [o-] |  • Effective nodes, etc.  |                  |
|  • Nodes lost         [o-] |  ------------------------ |                  |
|  ------------------------- |  (Data growth, Perf TBD)  |                  |
|  Namespaces (workload)     |                           |                  |
|  [Namespace card 1]        |                           |                  |
|  • Name [____] [Remove]   |                           |                  |
|  • Replication, Obj count, |                           |                  |
|    Record size, R/W %, etc. |                           |                  |
|  [+ Add namespace]         |                           |                  |
+---------------------------------------------------------------------------+
|  Load: [Load from defaults] [Load from collectinfo] (stub)                 |
+---------------------------------------------------------------------------+
```

- **Load from defaults** – Sets all inputs to defined minimum/safe defaults and refreshes outputs.
- **Export** – Downloads a JSON file containing all current inputs and outputs (standard output file format).
- **Reactivity** – Any slider/knob change sends current inputs to the backend; backend returns new outputs; front-end updates the output panel without a full page reload or "Apply" button.

## UI contract (for engine and loaders)

- **Inputs:** A single structure (e.g. JSON object) with keys for every capacity input. When the app supports multiple namespaces, inputs may be structured as cluster-level (nodes_per_cluster, devices_per_node, device_size_gb, available_memory_gb, overhead_pct, nodes_lost) plus per-namespace workload (replication_factor, master_object_count, avg_record_size_bytes, read_pct, write_pct, tombstone_pct, si_count, si_entries_per_object). Units and min/max per field are defined in the model. The contract (single logical input set, loaders, reactivity) still holds.
- **Outputs:** A single flat structure with keys for every displayed metric (storage utilization, data stored, total available, memory utilization, effective nodes, etc.). Engine accepts inputs and returns outputs; UI and Load buttons only read/write these structures.
- **Loaders** – Each returns the same input shape. "Load from defaults" is a function that returns the default input struct. "Load from collectinfo" (later) will return an input struct from parsed bundle/collectinfo. No UI-specific types in the engine.
