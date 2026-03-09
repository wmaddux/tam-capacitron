# Output panel organization

How outputs are grouped and prioritized so the flight-deck stays scannable. The Output panel uses **horizontal section dividers** (same style as the Input panel) to separate major blocks.

## Principles

- **Two main sections first:** Healthy cluster → Failure. Each section has a clear title and a horizontal line underneath.
- **Subsections inside each:** Within Healthy cluster, Storage and Memory are subsections. Within Failure, both storage and memory utilization are shown as primary rows.
- **Primary first:** Utilization % is the first row in each subsection; supporting metrics (GB, TB, counts) follow.
- **Future sections:** Data growth and Performance are reserved sections (placeholders) so the layout stays consistent as features are added.

## Section order

### 1. Healthy cluster

- **Storage** (subsection): Storage utilization % (primary) → Data stored (GB), Device total storage (TB), Total available storage (GB), Total device count.
- **Memory** (subsection): Memory utilization (base) % (primary) → Memory utilization (w/ tombstones) %, Available mem per cluster (GB), Total memory used base (GB).

### 2. Failure (N nodes lost)

- **Primary (both shown):** Failure storage utilization %, Failure memory utilization %.
- **Supporting:** Effective nodes, Failure total available storage (GB), Failure memory used (GB).

### 3. Data growth (future)

- Reserved for data growth / runway metrics.

### 4. Performance (future)

- Reserved for performance metrics (e.g. throughput, latency estimates).
