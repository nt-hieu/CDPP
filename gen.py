#!/usr/bin/env python3
"""
Best-effort reproduction script for Fig. 3 in:
  Reed, Campbell, Thomas (2024), "Does parking matter? The impact of parking
  time on last-mile delivery optimization".

What this script does
---------------------
1. Auto-detects the Illinois CDPP instance folder from either:
   - --data-root, or
   - --tree path/to/tree.txt, or
   - common relative paths.
2. Loads the base-case instances for Cook, Adams, Cumberland counties.
3. Computes four benchmark families used in Fig. 3:
   - CDPP (paper-inspired two-echelon heuristic from Section 3.3)
   - Relaxed M-S with alpha in {0.5, 0.6, 0.8}
   - Modified TSP (fixed service order, then optimize walking/driving/parking)
4. Produces:
   - fig3.png
   - fig3_values.csv
   - fig3_instance_details.csv

Important honesty note
----------------------
The uploaded paper text describes the CDPP model, the Section 3.3 heuristic,
and the Fig. 3 experimental setup, but it does NOT include the authors'
original private reproduction code for this exact paper, nor the Appendix A
model improvements in executable form. Because of that, this file is a
carefully engineered, research-style reproduction that follows the paper as
closely as possible with explicit, documented assumptions.

In particular:
- The CDPP implementation follows the paper's two-echelon heuristic structure:
  PA-R (parking assignment + routing) + SSA (service-set assignment).
- When gurobipy is available, PA-R and SSA are solved exactly for their own
  subproblems.
- Relaxed M-S is reproduced with a search over medoid/parking-cluster counts,
  evaluated under the weighted objective from Eq. (23), then converted to the
  realized completion time v + s*p as in Section 5.2.2.
- Modified TSP uses a TSP customer order and then exact dynamic programming for
  the best park-and-walk segmentation under that fixed order.

Therefore, this script is designed to be:
- faithful to the paper's definitions,
- readable and modifiable,
- runnable on the folder structure visible in tree.txt,
- and practical on a normal workstation.

Recommended environment
-----------------------
Python >= 3.10
Packages: numpy, pandas, matplotlib
Optional but strongly recommended: gurobipy

Example
-------
python gen.py --tree E:/sang/Hieu/parking_problem/tree.txt
python gen.py --data-root E:/sang/Hieu/parking_problem/data/illinois_cdpp_instances
"""

from __future__ import annotations

import argparse
import itertools
import math
import os
import random
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    import gurobipy as gp
    from gurobipy import GRB
    HAS_GUROBI = True
except Exception:
    HAS_GUROBI = False

# -----------------------------------------------------------------------------
# Configuration from the paper's base case (Section 5.1 / Fig. 3)
# -----------------------------------------------------------------------------

BASE_CASE_COUNTIES = ["Cook", "Adams", "Cumberland"]
BASE_CASE_INSTANCES = list(range(1, 11))
BASE_CASE_PARKING = {
    "Cook": 9.0,
    "Adams": 5.0,
    "Cumberland": 1.0,
}
BASE_CASE_Q = 3
BASE_CASE_F = 2.1
RELAXED_ALPHAS = [0.5, 0.6, 0.8]
RNG_SEED = 7

random.seed(RNG_SEED)
np.random.seed(RNG_SEED)


# -----------------------------------------------------------------------------
# Data structures
# -----------------------------------------------------------------------------

@dataclass
class Instance:
    county: str
    idx: int
    n_customers: int
    coords: pd.DataFrame
    drive: np.ndarray  # shape (n+1, n+1), includes depot 0
    walk: np.ndarray   # shape (n+1, n+1), entries for 1..n only, 0 row/col unused


@dataclass
class SolutionSummary:
    objective_optimized: float
    completion_time: float
    num_parks: int
    route_cost: float
    walking_cost: float
    loading_cost: float
    route: List[int]
    parking_spots: List[int]
    extra: Dict[str, object]


# -----------------------------------------------------------------------------
# Path discovery
# -----------------------------------------------------------------------------


def normalize_path_text(s: str) -> str:
    return s.strip().replace("\\", "/")



def derive_data_root_from_tree(tree_path: Path) -> Optional[Path]:
    """Parse tree.txt and recover the root .../data/illinois_cdpp_instances."""
    if not tree_path.exists():
        return None
    text = tree_path.read_text(encoding="utf-8", errors="ignore")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    pat = re.compile(
        r"^(?P<prefix>.*?)(?:/|\\)illinois_cdpp_instances(?:/|\\)data(?:/|\\)Urban_Rural_Instances(?:/|\\)(?:Cook|Adams|Cumberland)_1\.csv$",
        re.IGNORECASE,
    )
    for line in lines:
        m = pat.match(normalize_path_text(line))
        if m:
            prefix = m.group("prefix")
            root = Path(prefix) / "illinois_cdpp_instances"
            return root

    pat2 = re.compile(
        r"^(?P<root>.*?(?:/|\\)illinois_cdpp_instances)(?:/|\\)",
        re.IGNORECASE,
    )
    for line in lines:
        m = pat2.match(normalize_path_text(line))
        if m:
            return Path(m.group("root"))
    return None



def locate_data_root(explicit_root: Optional[str], tree_file: Optional[str]) -> Path:
    candidates: List[Path] = []
    if explicit_root:
        candidates.append(Path(explicit_root))

    if tree_file:
        derived = derive_data_root_from_tree(Path(tree_file))
        if derived is not None:
            candidates.append(derived)
            # also add the parent in case user passed data/illinois_cdpp_instances differently
            candidates.append(derived.parent)

    here = Path(__file__).resolve().parent
    candidates.extend([
        here,
        here / "data" / "illinois_cdpp_instances",
        here.parent / "data" / "illinois_cdpp_instances",
        Path.cwd(),
        Path.cwd() / "data" / "illinois_cdpp_instances",
    ])

    checked = []
    for cand in candidates:
        cand = cand.expanduser()
        checked.append(str(cand))

        # Case 1: user already points to .../illinois_cdpp_instances
        inst_dir = cand / "data" / "Urban_Rural_Instances"
        if inst_dir.exists():
            return cand

        # Case 2: user points directly to .../Urban_Rural_Instances
        if cand.name == "Urban_Rural_Instances" and cand.exists():
            return cand.parent.parent

        # Case 3: user points directly to .../data
        inst_dir = cand / "Urban_Rural_Instances"
        if inst_dir.exists():
            return cand.parent

    raise FileNotFoundError(
        "Could not locate the Illinois instance root. Checked:\n  - "
        + "\n  - ".join(checked)
        + "\nPass --data-root explicitly or pass --tree pointing to your tree.txt."
    )


# -----------------------------------------------------------------------------
# CSV loading
# -----------------------------------------------------------------------------


def parse_pair_key(key: str) -> Tuple[int, int]:
    m = re.match(r"\((\d+),\s*(\d+)\)", str(key).strip())
    if not m:
        raise ValueError(f"Cannot parse pair key: {key!r}")
    return int(m.group(1)), int(m.group(2))



def load_instance(data_root: Path, county: str, idx: int) -> Instance:
    inst_dir = data_root / "data" / "Urban_Rural_Instances"
    loc_file = inst_dir / f"{county}_{idx}.csv"
    drv_file = inst_dir / f"{county}_{idx}_Driving.csv"
    wlk_file = inst_dir / f"{county}_{idx}_Walking.csv"

    if not loc_file.exists():
        raise FileNotFoundError(f"Missing file: {loc_file}")
    if not drv_file.exists():
        raise FileNotFoundError(f"Missing file: {drv_file}")
    if not wlk_file.exists():
        raise FileNotFoundError(f"Missing file: {wlk_file}")

    coords = pd.read_csv(loc_file)
    n_plus_depot = len(coords)
    n = n_plus_depot - 1

    drv_df = pd.read_csv(drv_file)
    wlk_df = pd.read_csv(wlk_file)

    drive = np.full((n + 1, n + 1), np.inf, dtype=float)
    for _, row in drv_df.iterrows():
        i, j = parse_pair_key(row["key"])
        drive[i, j] = float(row["Time"])

    walk = np.full((n + 1, n + 1), np.inf, dtype=float)
    for _, row in wlk_df.iterrows():
        i, j = parse_pair_key(row["key"])
        walk[i, j] = float(row["Time"])

    # Defensive fill for diagonals
    for i in range(n + 1):
        drive[i, i] = 0.0
        walk[i, i] = 0.0

    return Instance(
        county=county,
        idx=idx,
        n_customers=n,
        coords=coords,
        drive=drive,
        walk=walk,
    )


# -----------------------------------------------------------------------------
# Small utilities
# -----------------------------------------------------------------------------


def route_cost(route: Sequence[int], drive: np.ndarray) -> float:
    return float(sum(drive[route[i], route[i + 1]] for i in range(len(route) - 1)))



def one_way_assignment_cost(parking: int, customers: Iterable[int], walk: np.ndarray) -> float:
    return float(sum(walk[parking, c] for c in customers))



def powerset_subsets(customers: Sequence[int], max_size: int) -> Iterable[Tuple[int, ...]]:
    for r in range(1, max_size + 1):
        for comb in itertools.combinations(customers, r):
            yield comb


class CostCache:
    def __init__(self, walk: np.ndarray, q: int):
        self.walk = walk
        self.q = q
        self.loop_cost_cache: Dict[Tuple[int, Tuple[int, ...]], float] = {}
        self.greedy_partition_cache: Dict[Tuple[int, Tuple[int, ...]], float] = {}
        self.exact_partition_cache: Dict[Tuple[int, Tuple[int, ...]], float] = {}

    def service_loop_cost(self, parking: int, subset: Sequence[int]) -> float:
        key = (parking, tuple(sorted(subset)))
        if key in self.loop_cost_cache:
            return self.loop_cost_cache[key]

        subset = tuple(sorted(subset))
        best = math.inf
        for perm in itertools.permutations(subset):
            total = self.walk[parking, perm[0]]
            for a, b in zip(perm[:-1], perm[1:]):
                total += self.walk[a, b]
            total += self.walk[perm[-1], parking]
            if total < best:
                best = total
        self.loop_cost_cache[key] = float(best)
        return float(best)

    def greedy_partition_cost(self, parking: int, customers: Sequence[int]) -> float:
        key = (parking, tuple(sorted(customers)))
        if key in self.greedy_partition_cache:
            return self.greedy_partition_cache[key]
        remaining: Set[int] = set(customers)
        total = 0.0
        while remaining:
            best_subset = None
            best_score = math.inf
            best_cost = math.inf
            rem_list = sorted(remaining)
            for subset in powerset_subsets(rem_list, self.q):
                cost = self.service_loop_cost(parking, subset)
                score = cost / len(subset)
                if (score < best_score - 1e-12) or (
                    abs(score - best_score) <= 1e-12 and len(subset) > len(best_subset or ())
                ):
                    best_score = score
                    best_cost = cost
                    best_subset = subset
            assert best_subset is not None
            total += best_cost
            remaining.difference_update(best_subset)
        self.greedy_partition_cache[key] = float(total)
        return float(total)

    def exact_partition_cost(self, parking: int, customers: Sequence[int], prefer_exact: bool = True) -> float:
        customers = tuple(sorted(customers))
        key = (parking, customers)
        if key in self.exact_partition_cache:
            return self.exact_partition_cache[key]

        if not customers:
            self.exact_partition_cache[key] = 0.0
            return 0.0

        # Small exact DP without any solver.
        if len(customers) <= 18:
            idx = {c: i for i, c in enumerate(customers)}
            subset_costs: List[Tuple[int, float]] = []
            for subset in powerset_subsets(customers, self.q):
                mask = 0
                for c in subset:
                    mask |= 1 << idx[c]
                subset_costs.append((mask, self.service_loop_cost(parking, subset)))
            nmask = 1 << len(customers)
            dp = [math.inf] * nmask
            dp[0] = 0.0
            for mask in range(nmask):
                if not math.isfinite(dp[mask]):
                    continue
                for smask, scost in subset_costs:
                    if mask & smask:
                        continue
                    new_mask = mask | smask
                    cand = dp[mask] + scost
                    if cand < dp[new_mask]:
                        dp[new_mask] = cand
            val = float(dp[-1])
            self.exact_partition_cache[key] = val
            return val

        if prefer_exact and HAS_GUROBI:
            subset_list = list(powerset_subsets(customers, self.q))
            subset_cost = [self.service_loop_cost(parking, s) for s in subset_list]
            with gp.Env(empty=True) as env:
                env.setParam("OutputFlag", 0)
                env.start()
                with gp.Model("ssa", env=env) as m:
                    z = m.addVars(len(subset_list), vtype=GRB.BINARY, name="z")
                    m.setObjective(gp.quicksum(subset_cost[t] * z[t] for t in range(len(subset_list))), GRB.MINIMIZE)
                    for c in customers:
                        m.addConstr(gp.quicksum(z[t] for t, s in enumerate(subset_list) if c in s) == 1)
                    m.optimize()
                    if m.Status == GRB.OPTIMAL:
                        val = float(m.ObjVal)
                        self.exact_partition_cache[key] = val
                        return val

        # Fallback for larger clusters when no exact solver is available.
        val = self.greedy_partition_cost(parking, customers)
        self.exact_partition_cache[key] = val
        return val


# -----------------------------------------------------------------------------
# TSP / ATSP
# -----------------------------------------------------------------------------


def exact_atsp_gurobi(nodes: Sequence[int], drive: np.ndarray) -> Optional[List[int]]:
    if not HAS_GUROBI:
        return None
    nodes = list(dict.fromkeys(nodes))
    if 0 not in nodes:
        nodes = [0] + nodes
    n_nodes = len(nodes)
    if n_nodes <= 2:
        return [0, 0]

    node_pos = {node: i for i, node in enumerate(nodes)}
    arc_list = [(i, j) for i in nodes for j in nodes if i != j]

    try:
        with gp.Env(empty=True) as env:
            env.setParam("OutputFlag", 0)
            env.start()
            with gp.Model("atsp", env=env) as m:
                x = m.addVars(arc_list, vtype=GRB.BINARY, name="x")
                f = m.addVars(arc_list, lb=0.0, vtype=GRB.CONTINUOUS, name="f")

                m.setObjective(gp.quicksum(drive[i, j] * x[i, j] for i, j in arc_list), GRB.MINIMIZE)

                for i in nodes:
                    m.addConstr(gp.quicksum(x[i, j] for j in nodes if j != i) == 1)
                    m.addConstr(gp.quicksum(x[j, i] for j in nodes if j != i) == 1)

                depot = 0
                m.addConstr(gp.quicksum(f[depot, j] for j in nodes if j != depot) == n_nodes - 1)
                for i in nodes:
                    if i == depot:
                        continue
                    m.addConstr(
                        gp.quicksum(f[j, i] for j in nodes if j != i)
                        - gp.quicksum(f[i, j] for j in nodes if j != i)
                        == 1
                    )
                for i, j in arc_list:
                    m.addConstr(f[i, j] <= (n_nodes - 1) * x[i, j])

                m.optimize()
                if m.Status != GRB.OPTIMAL:
                    return None

                succ = {}
                for i, j in arc_list:
                    if x[i, j].X > 0.5:
                        succ[i] = j
                route = [0]
                cur = 0
                seen = {0}
                while True:
                    nxt = succ[cur]
                    route.append(nxt)
                    if nxt == 0:
                        break
                    if nxt in seen:
                        return None
                    seen.add(nxt)
                    cur = nxt
                return route
    except Exception:
        return None



def nearest_neighbor_route(customers: Sequence[int], drive: np.ndarray, forced_first: Optional[int] = None) -> List[int]:
    unvisited = set(customers)
    route = [0]
    cur = 0
    if forced_first is not None:
        route.append(forced_first)
        unvisited.remove(forced_first)
        cur = forced_first
    while unvisited:
        nxt = min(unvisited, key=lambda j: (drive[cur, j], j))
        route.append(nxt)
        unvisited.remove(nxt)
        cur = nxt
    route.append(0)
    return route



def improve_route_local_search(route: List[int], drive: np.ndarray, max_rounds: int = 5) -> List[int]:
    best = list(route)
    best_cost = route_cost(best, drive)
    rounds = 0
    improved = True
    while improved and rounds < max_rounds:
        rounds += 1
        improved = False
        m = len(best)

        # Relocate
        for i in range(1, m - 1):
            for j in range(1, m - 1):
                if i == j:
                    continue
                cand = best[:]
                node = cand.pop(i)
                cand.insert(j, node)
                cand_cost = route_cost(cand, drive)
                if cand_cost + 1e-12 < best_cost:
                    best, best_cost = cand, cand_cost
                    improved = True
                    break
            if improved:
                break
        if improved:
            continue

        # 2-opt style segment reversal (works as a generic route improvement move,
        # even if the matrix is asymmetric, because we evaluate the full route cost).
        for i in range(1, m - 2):
            for j in range(i + 1, m - 1):
                cand = best[:i] + list(reversed(best[i:j + 1])) + best[j + 1:]
                cand_cost = route_cost(cand, drive)
                if cand_cost + 1e-12 < best_cost:
                    best, best_cost = cand, cand_cost
                    improved = True
                    break
            if improved:
                break
    return best



def solve_route(nodes: Sequence[int], drive: np.ndarray, prefer_exact: bool = False) -> List[int]:
    customers = [n for n in nodes if n != 0]
    if not customers:
        return [0, 0]

    if prefer_exact and HAS_GUROBI and len(customers) <= 25:
        exact = exact_atsp_gurobi([0] + customers, drive)
        if exact is not None:
            return exact

    seeds = sorted(customers, key=lambda j: (drive[0, j], j))[: min(8, len(customers))]
    routes = [nearest_neighbor_route(customers, drive, None)]
    routes.extend(nearest_neighbor_route(customers, drive, s) for s in seeds)
    best = None
    best_cost = math.inf
    for r in routes:
        r2 = improve_route_local_search(r, drive)
        c = route_cost(r2, drive)
        if c < best_cost:
            best = r2
            best_cost = c
    assert best is not None
    return best


# -----------------------------------------------------------------------------
# CDPP Section 3.3 heuristic: PA-R + SSA
# -----------------------------------------------------------------------------


def solve_par_gurobi(inst: Instance, parking_time: float) -> Tuple[List[int], Dict[int, List[int]]]:
    n = inst.n_customers
    customers = list(range(1, n + 1))
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()
        with gp.Model("par", env=env) as m:
            open_var = m.addVars(customers, vtype=GRB.BINARY, name="open")
            a = m.addVars(customers, customers, vtype=GRB.BINARY, name="a")
            m.setObjective(
                gp.quicksum(parking_time * open_var[i] for i in customers)
                + gp.quicksum(inst.walk[i, k] * a[i, k] for i in customers for k in customers),
                GRB.MINIMIZE,
            )
            for k in customers:
                m.addConstr(gp.quicksum(a[i, k] for i in customers) == 1)
            for i in customers:
                for k in customers:
                    m.addConstr(a[i, k] <= open_var[i])
                m.addConstr(open_var[i] <= gp.quicksum(a[i, k] for k in customers))
            m.optimize()
            if m.Status != GRB.OPTIMAL:
                raise RuntimeError("PA-R Gurobi model did not solve to optimality.")
            opened = [i for i in customers if open_var[i].X > 0.5]
            assign: Dict[int, List[int]] = {i: [] for i in opened}
            for k in customers:
                for i in opened:
                    if a[i, k].X > 0.5:
                        assign[i].append(k)
                        break
            return opened, assign



def solve_par_greedy(inst: Instance, parking_time: float) -> Tuple[List[int], Dict[int, List[int]]]:
    # Simple local-search fallback for the PA-R facility-location problem.
    n = inst.n_customers
    customers = list(range(1, n + 1))
    open_set: Set[int] = set(customers)

    def assign_cost(open_now: Set[int]) -> Tuple[float, Dict[int, List[int]]]:
        mapping = {i: [] for i in open_now}
        total = parking_time * len(open_now)
        for k in customers:
            best_i = min(open_now, key=lambda i: (inst.walk[i, k], i))
            mapping[best_i].append(k)
            total += inst.walk[best_i, k]
        return total, mapping

    best_val, best_map = assign_cost(open_set)
    improved = True
    while improved and len(open_set) > 1:
        improved = False
        best_move = None
        for i in list(open_set):
            cand_open = set(open_set)
            cand_open.remove(i)
            cand_val, cand_map = assign_cost(cand_open)
            if cand_val + 1e-12 < best_val:
                best_val = cand_val
                best_move = (cand_open, cand_map)
        if best_move is not None:
            open_set, best_map = best_move
            improved = True
    return sorted(open_set), {i: sorted(v) for i, v in best_map.items()}



def solve_cdpp(inst: Instance, parking_time: float, load_time: float, q: int, cache: CostCache, prefer_exact: bool) -> SolutionSummary:
    if prefer_exact and HAS_GUROBI:
        opened, assigned = solve_par_gurobi(inst, parking_time)
    else:
        opened, assigned = solve_par_greedy(inst, parking_time)

    route = solve_route(opened, inst.drive, prefer_exact=prefer_exact and len(opened) <= 25)
    route_drive_cost = route_cost(route, inst.drive)

    walking_cost = 0.0
    per_parking = {}
    for p in opened:
        cluster = assigned.get(p, [])
        if not cluster:
            continue
        w = cache.exact_partition_cost(p, cluster, prefer_exact=prefer_exact)
        per_parking[p] = {"customers": cluster, "walking": w}
        walking_cost += w

    loading_cost = inst.n_customers * load_time
    completion = route_drive_cost + len(opened) * parking_time + walking_cost + loading_cost
    return SolutionSummary(
        objective_optimized=completion,
        completion_time=completion,
        num_parks=len(opened),
        route_cost=route_drive_cost,
        walking_cost=walking_cost,
        loading_cost=loading_cost,
        route=route,
        parking_spots=opened,
        extra={"assigned": per_parking, "method": "CDPP Section 3.3 heuristic"},
    )


# -----------------------------------------------------------------------------
# Relaxed M-S benchmark (Eq. 23 + realized completion v + s*p)
# -----------------------------------------------------------------------------


def assign_to_medoids(medoids: Sequence[int], walk: np.ndarray, customers: Sequence[int]) -> Dict[int, List[int]]:
    clusters = {m: [] for m in medoids}
    for c in customers:
        m = min(medoids, key=lambda x: (walk[x, c], x))
        clusters[m].append(c)
    return {m: sorted(v) for m, v in clusters.items() if v}



def update_medoids(clusters: Dict[int, List[int]], walk: np.ndarray) -> List[int]:
    new_medoids = []
    for _, cluster in sorted(clusters.items()):
        best = min(cluster, key=lambda cand: (sum(walk[cand, c] for c in cluster), cand))
        new_medoids.append(best)
    return sorted(new_medoids)



def kmedoids_oneway(customers: Sequence[int], walk: np.ndarray, m: int, max_iter: int = 20) -> Dict[int, List[int]]:
    customers = list(customers)
    if m >= len(customers):
        return {c: [c] for c in customers}

    # Greedy farthest-first style initialization under walking distance.
    medoids = [min(customers, key=lambda c: (sum(walk[c, x] for x in customers), c))]
    while len(medoids) < m:
        remaining = [c for c in customers if c not in medoids]
        next_medoid = max(
            remaining,
            key=lambda c: min(walk[c, mm] for mm in medoids),
        )
        medoids.append(next_medoid)
    medoids = sorted(medoids)

    for _ in range(max_iter):
        clusters = assign_to_medoids(medoids, walk, customers)
        new_medoids = update_medoids(clusters, walk)
        if sorted(new_medoids) == sorted(medoids):
            return clusters
        medoids = sorted(new_medoids)
    return assign_to_medoids(medoids, walk, customers)



def surrogate_cluster_walk(medoid: int, cluster: Sequence[int], walk: np.ndarray) -> float:
    # Cheap scoring surrogate used only during model search.
    # PA-R in the paper uses sum W(i,k); we keep that spirit here.
    return float(sum(walk[medoid, c] for c in cluster))



def search_relaxed_ms(inst: Instance, alpha: float, parking_time: float, load_time: float, q: int,
                      cache: CostCache, prefer_exact: bool, all_m: bool = True) -> SolutionSummary:
    customers = list(range(1, inst.n_customers + 1))
    if all_m:
        m_candidates = list(range(1, inst.n_customers + 1))
    else:
        m_candidates = sorted(set(list(range(1, min(15, inst.n_customers) + 1)) + [18, 21, 24, 27, 30, 35, 40, 45, inst.n_customers]))
        m_candidates = [m for m in m_candidates if 1 <= m <= inst.n_customers]

    approx_records = []
    clusterings = {}

    for m in m_candidates:
        clusters = kmedoids_oneway(customers, inst.walk, m)
        medoids = sorted(clusters)
        route = solve_route(medoids, inst.drive, prefer_exact=False)
        drive_cost = route_cost(route, inst.drive)
        surrogate_walk = sum(surrogate_cluster_walk(md, cl, inst.walk) for md, cl in clusters.items())
        surrogate_obj = alpha * drive_cost + (1.0 - alpha) * surrogate_walk + inst.n_customers * load_time
        approx_records.append((surrogate_obj, m, medoids, route))
        clusterings[m] = clusters

    approx_records.sort(key=lambda x: x[0])
    top_ms = sorted(set(m for _, m, _, _ in approx_records[: min(6, len(approx_records))]))

    best: Optional[SolutionSummary] = None
    best_obj = math.inf
    for m in top_ms:
        clusters = clusterings[m]
        medoids = sorted(clusters)
        route = solve_route(medoids, inst.drive, prefer_exact=prefer_exact and len(medoids) <= 20)
        drive_cost = route_cost(route, inst.drive)
        walking_cost = 0.0
        detail = {}
        for md, cl in clusters.items():
            w = cache.exact_partition_cost(md, cl, prefer_exact=prefer_exact)
            detail[md] = {"customers": cl, "walking": w}
            walking_cost += w
        loading_cost = inst.n_customers * load_time
        weighted_obj = alpha * drive_cost + (1.0 - alpha) * walking_cost + loading_cost
        completion = drive_cost + len(medoids) * parking_time + walking_cost + loading_cost
        sol = SolutionSummary(
            objective_optimized=weighted_obj,
            completion_time=completion,
            num_parks=len(medoids),
            route_cost=drive_cost,
            walking_cost=walking_cost,
            loading_cost=loading_cost,
            route=route,
            parking_spots=medoids,
            extra={
                "assigned": detail,
                "alpha": alpha,
                "search_top_ms": top_ms,
                "method": "Relaxed M-S search over parking-cluster count",
            },
        )
        if weighted_obj < best_obj:
            best_obj = weighted_obj
            best = sol

    assert best is not None
    return best


# -----------------------------------------------------------------------------
# Modified TSP benchmark
# -----------------------------------------------------------------------------


def precompute_episode_costs(order: Sequence[int], inst: Instance, parking_time: float, load_time: float, q: int) -> Dict[int, np.ndarray]:
    n = len(order)
    customers = list(range(1, inst.n_customers + 1))
    # 1-indexed segment tables: cost[p][l, r] valid for 1<=l<=r<=n
    cost_by_parking: Dict[int, np.ndarray] = {}

    for p in customers:
        seg = np.full((n + 2, n + 2), np.inf, dtype=float)
        chunk = np.full((n + 2, n + 2), np.inf, dtype=float)

        for l in range(1, n + 1):
            running = 0.0
            for r in range(l, min(n, l + q - 1) + 1):
                if r == l:
                    c = order[l - 1]
                    running = inst.walk[p, c] + inst.walk[c, p]
                else:
                    prev = order[r - 2]
                    cur = order[r - 1]
                    # extend p->...->prev->p into p->...->prev->cur->p
                    running = running - inst.walk[prev, p] + inst.walk[prev, cur] + inst.walk[cur, p]
                chunk[l, r] = running + (r - l + 1) * load_time

        for l in range(n, 0, -1):
            for r in range(l, n + 1):
                best = math.inf
                for m in range(l, min(r, l + q - 1) + 1):
                    tail = 0.0 if m == r else seg[m + 1, r]
                    cand = chunk[l, m] + tail
                    if cand < best:
                        best = cand
                seg[l, r] = parking_time + best
        cost_by_parking[p] = seg
    return cost_by_parking



def solve_modified_tsp(inst: Instance, parking_time: float, load_time: float, q: int, prefer_exact: bool) -> SolutionSummary:
    all_customers = list(range(1, inst.n_customers + 1))
    tsp_route = solve_route(all_customers, inst.drive, prefer_exact=prefer_exact and inst.n_customers <= 25)
    order = tsp_route[1:-1]
    n = len(order)

    episode_cost = precompute_episode_costs(order, inst, parking_time, load_time, q)
    customers = list(range(1, inst.n_customers + 1))

    dp = np.full((n + 1, inst.n_customers + 1), np.inf, dtype=float)
    prev_state: Dict[Tuple[int, int], Tuple[int, int]] = {}
    dp[0, 0] = 0.0

    for s in range(0, n):
        for prev_p in range(0, inst.n_customers + 1):
            base = dp[s, prev_p]
            if not math.isfinite(base):
                continue
            for e in range(s + 1, n + 1):
                for p in customers:
                    cand = base + inst.drive[prev_p, p] + episode_cost[p][s + 1, e]
                    if cand + 1e-12 < dp[e, p]:
                        dp[e, p] = cand
                        prev_state[(e, p)] = (s, prev_p)

    best_total = math.inf
    best_p = None
    for p in customers:
        cand = dp[n, p] + inst.drive[p, 0]
        if cand < best_total:
            best_total = cand
            best_p = p
    assert best_p is not None

    # Reconstruct parking episodes.
    episodes: List[Tuple[int, int, int]] = []
    cur = (n, best_p)
    while cur in prev_state:
        s, prev_p = prev_state[cur]
        e, p = cur
        episodes.append((s + 1, e, p))
        cur = (s, prev_p)
    episodes.reverse()

    parking_spots = [p for _, _, p in episodes]
    route = [0] + parking_spots + [0]
    route_drive_cost = route_cost(route, inst.drive)
    walking_plus_loading = best_total - route_drive_cost
    loading_cost = inst.n_customers * load_time
    walking_cost = walking_plus_loading - len(episodes) * parking_time

    return SolutionSummary(
        objective_optimized=best_total,
        completion_time=best_total,
        num_parks=len(episodes),
        route_cost=route_drive_cost,
        walking_cost=walking_cost,
        loading_cost=loading_cost,
        route=route,
        parking_spots=parking_spots,
        extra={
            "customer_order": order,
            "episodes": episodes,
            "method": "Modified TSP DP over a fixed TSP service order",
        },
    )


# -----------------------------------------------------------------------------
# Experiment runner
# -----------------------------------------------------------------------------


def percent_reduction(baseline: float, improved: float) -> float:
    return 100.0 * (baseline - improved) / baseline



def run_one_instance(inst: Instance, q: int, load_time: float, parking_time: float, prefer_exact: bool,
                     relaxed_all_m: bool) -> Dict[str, SolutionSummary]:
    cache = CostCache(inst.walk, q=q)
    out: Dict[str, SolutionSummary] = {}

    out["CDPP"] = solve_cdpp(inst, parking_time, load_time, q, cache, prefer_exact)
    out["Modified TSP"] = solve_modified_tsp(inst, parking_time, load_time, q, prefer_exact)

    for alpha in RELAXED_ALPHAS:
        key = f"Relaxed M-S (alpha={alpha:.1f})"
        out[key] = search_relaxed_ms(inst, alpha, parking_time, load_time, q, cache, prefer_exact, all_m=relaxed_all_m)
    return out



def build_fig3(details_df: pd.DataFrame, output_png: Path) -> pd.DataFrame:
    bench_order = [
        "Relaxed M-S (alpha=0.5)",
        "Relaxed M-S (alpha=0.6)",
        "Relaxed M-S (alpha=0.8)",
        "Modified TSP",
    ]
    county_order = ["Cook", "Adams", "Cumberland"]

    reduced = []
    for county in county_order:
        sub = details_df[details_df["county"] == county]
        cdpp = sub[sub["benchmark"] == "CDPP"][["instance_id", "completion_time"]].rename(columns={"completion_time": "cdpp_time"})
        for bench in bench_order:
            b = sub[sub["benchmark"] == bench][["instance_id", "completion_time"]].rename(columns={"completion_time": "baseline_time"})
            merged = cdpp.merge(b, on="instance_id", how="inner")
            merged["pct_reduction"] = 100.0 * (merged["baseline_time"] - merged["cdpp_time"]) / merged["baseline_time"]
            reduced.append({
                "county": county,
                "benchmark": bench,
                "avg_pct_reduction": merged["pct_reduction"].mean(),
            })

    fig_df = pd.DataFrame(reduced)

    x = np.arange(len(county_order), dtype=float)
    width = 0.18
    fig, ax = plt.subplots(figsize=(10, 5.2))
    for offset, bench in zip([-1.5, -0.5, 0.5, 1.5], bench_order):
        vals = [float(fig_df[(fig_df["county"] == county) & (fig_df["benchmark"] == bench)]["avg_pct_reduction"].iloc[0]) for county in county_order]
        ax.bar(x + offset * width, vals, width, label=bench)

    ax.set_xticks(x)
    ax.set_xticklabels(county_order)
    ax.set_ylabel("Average percent reduction in completion time")
    ax.set_title("Fig. 3 reproduction: CDPP relative to benchmarks")
    ax.legend(frameon=False, ncols=2)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return fig_df


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reproduce Fig. 3 from the parking-matter paper.")
    p.add_argument("--data-root", type=str, default=None,
                   help="Root folder that contains data/Urban_Rural_Instances (typically .../data/illinois_cdpp_instances).")
    p.add_argument("--tree", type=str, default=None,
                   help="Path to tree.txt. The script will auto-detect the data root from it.")
    p.add_argument("--outdir", type=str, default="./fig3_output",
                   help="Directory for fig3.png and CSV outputs.")
    p.add_argument("--counties", nargs="*", default=BASE_CASE_COUNTIES,
                   help="Counties to run. Default: Cook Adams Cumberland")
    p.add_argument("--instances", nargs="*", type=int, default=BASE_CASE_INSTANCES,
                   help="Instance IDs to run. Default: 1..10")
    p.add_argument("--q", type=int, default=BASE_CASE_Q, help="Delivery-person capacity q. Default: 3")
    p.add_argument("--f", type=float, default=BASE_CASE_F, help="Loading time per package. Default: 2.1")
    p.add_argument("--solver-mode", choices=["auto", "gurobi", "heuristic"], default="auto",
                   help="auto=use gurobi when available, else heuristic.")
    p.add_argument("--relaxed-search", choices=["all", "coarse"], default="all",
                   help="How many parking-cluster counts m to search for Relaxed M-S.")
    return p.parse_args()



def main() -> None:
    args = parse_args()
    prefer_exact = (args.solver_mode == "gurobi") or (args.solver_mode == "auto" and HAS_GUROBI)
    relaxed_all_m = args.relaxed_search == "all"

    data_root = locate_data_root(args.data_root, args.tree)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Data root: {data_root}")
    print(f"[INFO] Gurobi available: {HAS_GUROBI}")
    print(f"[INFO] Using exact sub-solvers when possible: {prefer_exact}")

    detail_rows = []
    t0 = time.time()

    for county in args.counties:
        if county not in BASE_CASE_PARKING:
            raise ValueError(f"County {county!r} not in base-case parking map: {sorted(BASE_CASE_PARKING)}")
        p_time = BASE_CASE_PARKING[county]

        for idx in args.instances:
            print(f"\n[RUN] County={county} instance={idx}")
            inst = load_instance(data_root, county, idx)
            sols = run_one_instance(inst, q=args.q, load_time=args.f, parking_time=p_time,
                                    prefer_exact=prefer_exact, relaxed_all_m=relaxed_all_m)
            for bench, sol in sols.items():
                detail_rows.append({
                    "county": county,
                    "instance_id": idx,
                    "benchmark": bench,
                    "optimized_objective": sol.objective_optimized,
                    "completion_time": sol.completion_time,
                    "num_parks": sol.num_parks,
                    "route_cost": sol.route_cost,
                    "walking_cost": sol.walking_cost,
                    "loading_cost": sol.loading_cost,
                    "parking_time": p_time,
                    "q": args.q,
                    "f": args.f,
                })
                print(f"  - {bench:24s} completion={sol.completion_time:9.3f}  parks={sol.num_parks:2d}")

    details_df = pd.DataFrame(detail_rows)
    details_csv = outdir / "fig3_instance_details.csv"
    details_df.to_csv(details_csv, index=False)

    fig_df = build_fig3(details_df, outdir / "fig3.png")
    fig_df.to_csv(outdir / "fig3_values.csv", index=False)

    # Also write a compact report with average completion times.
    avg_times = details_df.groupby(["county", "benchmark"], as_index=False)["completion_time"].mean()
    avg_times.to_csv(outdir / "fig3_avg_completion_times.csv", index=False)

    elapsed = time.time() - t0
    print("\n[OK] Finished.")
    print(f"[OK] Wrote: {outdir / 'fig3.png'}")
    print(f"[OK] Wrote: {outdir / 'fig3_values.csv'}")
    print(f"[OK] Wrote: {details_csv}")
    print(f"[OK] Runtime: {elapsed / 60.0:.2f} minutes")


if __name__ == "__main__":
    main()
