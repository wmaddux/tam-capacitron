# Full-page flight-deck mockups (inputs + outputs)

Standalone HTML mockups for the **full capacity planning page** (inputs and outputs) so you can compare layout and prioritization before changing the real app.

**Base wireframe:** **[mockup-cluster-namespace-split-with-definition.html](mockup-cluster-namespace-split-with-definition.html)** (three columns: Inputs | Outputs | Definition; Cluster + Namespaces cards; parameter help on label click). The **live app** ([app/static/index.html](../../app/static/index.html)) extends this with: cluster default storage pattern; per-namespace storage pattern (HMA/In-Memory/All Flash/DMD/Custom), Custom placement, compression, capacity thresholds; column 3 **Show my work** panel (step-by-step storage utilization); Data growth and Performance output cards; Load from collectinfo "Loading…" state. For current UI scope and file map, see **[MANIFEST.md](../../MANIFEST.md)**. See [docs/STRAWMAN_UI_AND_FLOW.md](../STRAWMAN_UI_AND_FLOW.md) for flow. See **[OUTPUT_ORGANIZATION.md](OUTPUT_ORGANIZATION.md)** for how outputs are grouped.

## How to view

Open each file in a browser (double-click or drag into the browser, or use “Open with” → your browser):

- **mockup-a-gauge-cards.html** – **Inputs:** Grouped into Topology, Server/memory, Workload, Resilience with section titles and compact slider rows. **Outputs:** Gauge cards—each group has one large primary metric and supporting metrics in a row below.
- **mockup-b-instrument-stack.html** – **Inputs:** Same four groups with left-accent section titles. **Outputs:** Vertical stack of “instruments” with a left accent bar; primary value prominent, supporting metrics inline to the right.
- **mockup-c-headline-strip.html** – **Inputs:** Same four groups with section titles. **Outputs:** Top row of three headline tiles (Storage %, Memory %, Failure storage %); below, grouped detail rows for all supporting metrics.

## Organization

- **Inputs** are grouped as: Topology (replication, nodes, devices, size), Server/memory (memory per node, overhead), Workload (object count, record size, read/write/tombstone, SI), Resilience (nodes lost). Toolbar: Load from defaults, Export.
- **Outputs** emphasize primary metrics (e.g. Storage utilization %, Memory utilization %) with supporting metrics (Data stored, Device total storage, etc.) secondary. Groups: Storage (healthy), Memory (healthy and w/ tombstones), Failure scenario, Counts.

## Light-theme variants (lighter background, darker text)

Three additional mockups use **light backgrounds and dark text** for stronger contrast and readability:

- **mockup-light-a-cool-neutral.html** – Cool neutral: light grey page (`#f0f2f5`), white panels, dark grey/black text (`#1a1d24`, `#0f1419` for values), blue accent (`#2563eb`) for sliders and hover.
- **mockup-light-b-warm.html** – Warm: cream/off-white background (`#f5f0e8`), cream cards (`#fefdfb`), dark brown/charcoal text (`#2c2419`, `#1a1510` for values), amber accent (`#b45309`).
- **mockup-light-c-slate.html** – Slate: light blue-grey base (`#e8ecf1`), white panels, slate text (`#1e293b`, `#0f172a` for values), teal accent (`#0d9488`).

Same layout as mockup C (headline strip + grouped details, full inputs + outputs). Open each in a browser to compare.

## Primary vs secondary contrast (light A base)

Three variants stress **primary** (e.g. utilization %) vs **secondary** (supporting metrics) more strongly:

- **mockup-light-a-contrast-1-size.html** – **Size + weight:** Primary rows use a larger value (1.4rem), bolder label (0.9rem, font-weight 600), and extra padding. Secondary stay at 0.75rem.
- **mockup-light-a-contrast-2-block.html** – **Block / box:** Related outputs are grouped in one card per topic (Storage card, Memory card, Failure card). Light grey card background, border, padding; primary metric in each card is larger/bolder. The chosen wireframe is now the cluster-namespace-with-definition mockup below, which keeps this output card style.
- **mockup-light-a-contrast-3-accent.html** – **Accent bar + color:** Primary rows have a 4px blue left border and the value in accent color (blue), larger (1.2rem); secondary stay default.

Same content and section structure (Healthy cluster, Failure, Data growth, Performance). Open each to compare.

## Cluster vs namespace (future multi-namespace)

- **[mockup-cluster-namespace-split.html](mockup-cluster-namespace-split.html)** – Wireframe that separates **cluster-wide** parameters (topology, server/memory, resilience) from **namespace-specific** parameters (workload). Includes namespace cards with Add/Remove and "+ Add namespace".
- **[mockup-cluster-namespace-split-with-definition.html](mockup-cluster-namespace-split-with-definition.html)** – **Base wireframe.** Same as above with a **Definition** panel on the right. Clicking a parameter label shows its definition in this third column.
- **[mockup-capacity-combined.html](mockup-capacity-combined.html)** – **Current app reference.** Static mockup matching app/static/index.html: cluster default storage pattern, per-namespace storage pattern pills (HMA/In-Memory/All Flash/DMD/Custom), compression, capacity thresholds, Parameter help + Show my work panels, By pattern breakdown, Data growth and Performance output cards. Use for project context.
- **[CLUSTER_VS_NAMESPACE_WIREFRAME.md](CLUSTER_VS_NAMESPACE_WIREFRAME.md)** – Table of cluster-wide vs namespace-specific parameters and reference to the Workload sheet in Tool_Aerospike_Sizing_Estimator.

## Applying the chosen wireframe

The base wireframe is **mockup-cluster-namespace-split-with-definition.html**. The real app (`app/static/index.html`) uses this layout and adds storage patterns, Show my work, and related UI (see [MANIFEST.md](../../MANIFEST.md) for current scope). When changing the app, keep the mockup’s three-column layout (Inputs | Outputs | Definition), Cluster + Namespaces input structure, Parameter help + Show my work column, output cards, and light theme (see [STRAWMAN_UI_AND_FLOW.md](../STRAWMAN_UI_AND_FLOW.md)).
