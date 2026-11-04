# RoverMind — Algorithmic Foundations

This document provides a rigorous mathematical and algorithmic explanation of the core algorithms implemented in RoverMind: the **Custom A* Path Planner** and the **Terrain Risk Costmap Engine**.

---

# 1. Custom A* Pathfinding Engine

The pathfinding service (`backend/app/services/path_planner.py`) implements an exact version of the A* heuristic search algorithm on a 2D discrete grid with non-uniform cell traversal costs.

## 1.1 Objective Function & Cost Formulation

A* evaluates search nodes using the evaluation function:

$$f(n) = g(n) + h(n)$$

Where:
- $g(n)$: The exact cumulative path cost incurred from the start node $s$ to the current node $n$.
- $h(n)$: An admissible heuristic estimating the lowest possible cost from $n$ to the goal node $\gamma$.
- $f(n)$: The estimated total cost of the cheapest solution passing through node $n$.

### Transition Cost Formulation
When moving from node $u = (r_1, c_1)$ to neighbor $v = (r_2, c_2)$, the step traversal cost is weighted by the geometric distance and the destination cell's cost:

$$\text{cost}(u, v) = \Delta d_{\text{geo}}(u, v) \times \text{cost\_grid}[r_2][c_2]$$

Where:
- For cardinal moves (North, South, East, West):
  $$\Delta d_{\text{geo}} = 1.0$$
- For diagonal moves (NE, NW, SE, SW):
  $$\Delta d_{\text{geo}} = \sqrt{2} \approx 1.41421356$$
- $\text{cost\_grid}[r_2][c_2]$: A non-negative finite floating-point value assigned to the destination cell.

---

## 1.2 Admissible Heuristics

To guarantee optimality, the heuristic $h(n)$ must never overestimate the true remaining cost ($h(n) \le h^*(n)$). 

RoverMind enforces admissibility by scaling geometric distance by the global minimum traversable cell cost:

$$c_{\min} = \min_{(r, c) \in \text{grid}, \text{grid}[r][c] \neq \text{None}} \text{cost\_grid}[r][c]$$

### 1. Manhattan Distance (4-Way Cardinal Movement)
When `allow_diagonal=False`, movement is restricted to 4 cardinal directions. The heuristic is:

$$h(n) = (|r - r_{\gamma}| + |c - c_{\gamma}|) \times c_{\min}$$

### 2. Octile Distance (8-Way Movement with Diagonals)
When `allow_diagonal=True`, the agent may take diagonal steps. The shortest distance on an 8-connected grid with diagonal cost $\sqrt{2}$ is the Octile distance:

$$\Delta r = |r - r_{\gamma}|, \quad \Delta c = |c - c_{\gamma}|$$
$$h(n) = \left[ \max(\Delta r, \Delta c) + (\sqrt{2} - 1) \min(\Delta r, \Delta c) \right] \times c_{\min}$$

---

## 1.3 Diagonal Corner-Cutting Prevention

In physical planetary robotics, moving diagonally past the sharp corner of a high obstacle risks collision due to rover chassis width and wheel clearance.

RoverMind enforces strict corner-cutting prevention:
For any proposed diagonal move from $(r, c)$ to $(r + dr, c + dc)$ where $|dr| = 1$ and $|dc| = 1$:

$$\text{Valid Move} \iff \begin{cases}
\text{cost\_grid}[r + dr][c] \neq \text{None} \\
\text{and} \\
\text{cost\_grid}[r][c + dc] \neq \text{None}
\end{cases}$$

If either adjacent cardinal cell is impassable (`None`), the diagonal step is disallowed.

```
Example:
[ . ] [ X ]    Rover at (1, 0) cannot move diagonally to (0, 1)
[ R ] [ . ]    because cell (0, 0) is blocked ('X')!
```

---

## 1.4 Open Set Priority Queue & Tie-Breaking

The open set is implemented using Python's `heapq` (binary min-heap). 
Elements are stored as 5-tuples:

$$(f\_score, \ h\_score, \ tie\_breaker, \ (r, c), \ g\_score\_at\_insertion)$$

- **$f\_score$**: Primary sort key.
- **$h\_score$**: Secondary sort key (preferring nodes closer to the goal).
- **$tie\_breaker$**: Monotonically increasing counter ensuring deterministic FIFO resolution between nodes with identical scores.
- **Stale Entry Elimination**: When a node is popped, if $current\_g > g\_score.get(current)$, the entry is stale and discarded immediately.

---

## 1.5 Worked Example on a $3 \times 3$ Grid

Consider the following cost grid:

```
Row 0:  [ 1.0 ]  [ 1.0 ]  [ 1.0 ]
Row 1:  [ None]  [ None]  [ 1.0 ]
Row 2:  [ 1.0 ]  [ 1.0 ]  [ 1.0 ]
```
- **Start**: $(0, 0)$
- **Goal**: $(2, 0)$
- **Movement**: Cardinal only (`allow_diagonal=False`)

### Step-by-Step Execution:
1. **Initialize**:
   - $g((0, 0)) = 0.0$
   - $h((0, 0)) = (|0 - 2| + |0 - 0|) \times 1.0 = 2.0$
   - Push $(2.0, (0, 0))$ to Open Set.
2. **Expand $(0, 0)$**:
   - Neighbors: $(0, 1)$ (East). Neighbor $(1, 0)$ is blocked (`None`).
   - $g((0, 1)) = 0.0 + 1.0 \times 1.0 = 1.0$
   - $h((0, 1)) = (|0 - 2| + |1 - 0|) = 3.0$
   - $f((0, 1)) = 4.0$
3. **Expand $(0, 1)$**:
   - Neighbors: $(0, 2)$ (East). $(1, 1)$ is blocked (`None`).
   - $g((0, 2)) = 1.0 + 1.0 = 2.0$, $f((0, 2)) = 2.0 + 4.0 = 6.0$
4. **Expand $(0, 2)$**:
   - Neighbors: $(1, 2)$ (South).
   - $g((1, 2)) = 2.0 + 1.0 = 3.0$, $f((1, 2)) = 3.0 + 3.0 = 6.0$
5. **Expand $(1, 2)$**:
   - Neighbors: $(2, 2)$ (South).
   - $g((2, 2)) = 3.0 + 1.0 = 4.0$, $f((2, 2)) = 4.0 + 2.0 = 6.0$
6. **Expand $(2, 2)$**:
   - Neighbors: $(2, 1)$ (West).
   - $g((2, 1)) = 4.0 + 1.0 = 5.0$, $f((2, 1)) = 5.0 + 1.0 = 6.0$
7. **Expand $(2, 1)$**:
   - Neighbors: $(2, 0)$ (West, Goal!).
   - $g((2, 0)) = 5.0 + 1.0 = 6.0$, $f((2, 0)) = 6.0 + 0.0 = 6.0$
8. **Goal Reached**:
   - Reconstructed Path: `[(0, 0), (0, 1), (0, 2), (1, 2), (2, 2), (2, 1), (2, 0)]`
   - Total Weighted Cost: $6.0$
   - Geometric Length: $6.0$

---

## 1.6 Complexity Analysis

For a grid of $R$ rows and $C$ columns ($V = R \times C$ nodes, $E \le 8V$ edges):
- **Time Complexity**:
  - Worst Case: $O(V \log V)$ when exploring large open spaces.
  - Heuristic Pruning: With admissible Octile/Manhattan heuristics, average search time drops significantly towards $O(L \log V)$ where $L$ is path length.
- **Space Complexity**:
  - Open Set: $O(V)$ in binary heap.
  - Closed Set / Lookup: $g\_score$ and $came\_from$ dictionaries occupy $O(V)$ memory.

---

# 2. Terrain Risk Costmap Compilation

The costmap engine (`backend/app/services/terrain_costmap.py`) executes deterministic conversion of discrete string categories into numerical costs.

## Mathematical Mapping
Let $T(r, c) \in \Sigma$ be the categorical label of cell $(r, c)$ from alphabet $\Sigma = \{\text{clear}, \text{rocky}, \text{loose}, \text{obstacle}, \text{unknown}\}$.

The cost function $C: \Sigma \to \mathbb{R}^+ \cup \{\text{None}\}$ is defined as:

$$C(\tau) = \begin{cases}
1.0 & \text{if } \tau = \text{"clear"} \\
3.0 & \text{if } \tau = \text{"rocky"} \\
5.0 & \text{if } \tau = \text{"loose"} \\
2.0 & \text{if } \tau = \text{"unknown"} \\
\text{None} & \text{if } \tau = \text{"obstacle"}
\end{cases}$$

## Safety Invariant
Any cell mapped to `None` has an infinite effective impedance:

$$\forall u, \quad \text{if } \text{cost}(v) = \text{None} \implies \text{cost}(u, v) = \infty$$

The A* planner strictly prunes all edges leading to $v$, guaranteeing that impassable obstacles are never traversed.
