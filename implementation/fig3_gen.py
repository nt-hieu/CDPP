"""
fig3_gen.py
===========
Reproduce Figure 3 from:
  "Does Parking Matter? The Impact of Parking Time on Last-Mile
   Delivery Optimization"
  Sara Reed, Ann Melissa Campbell, Barrett W. Thomas
  Transportation Research Part E 181 (2024) 103391

Uses Illinois county instance data (Cook, Adams, Cumberland) from:
  https://github.com/INFORMSJoC/2023.0177

Implements:
  1. CDPP heuristic (Section 3.3: PA-R + SSA + TSP)
  2. TSP baseline = Relaxed M-S alpha=0.5  (Section 5.2.2)
  3. Relaxed M-S alpha=0.6 proxy
  4. Relaxed M-S alpha=0.8 proxy
  5. Modified TSP (Section 5.2.1: route-first cluster-second)

Base case (Section 5.1):
  n=50 customers, q=3 packages, f=2.1 min
  Cook County (urban):      p = 9 min
  Adams County (suburban):  p = 5 min
  Cumberland County (rural): p = 1 min
"""

import os
import csv
import ast
import itertools
import time as time_mod
import numpy as np

# Gurobi
import gurobipy as gp
from gurobipy import GRB

import matplotlib
matplotlib.use('Agg')           # non-interactive backend (safe on Windows)
import matplotlib.pyplot as plt

# =====================================================================
# Configuration
# =====================================================================
DATA_DIR = os.path.join(
    os.path.dirname(__file__),
    "data", "illinois_cdpp_instances", "data", "Urban_Rural_Instances"
)

Q_CAP      = 3        # carrying capacity (packages)
F_TIME     = 2.1      # loading time per package (minutes)
N_INSTANCES = 5       # Reduced for testing (paper uses 10)
N_CUSTOMERS = 15      # User requested n=15 for Gurobi license limits

COUNTIES = {
    'Cook County':       {'p': 9, 'prefix': 'Cook'},
    'Adams County':      {'p': 5, 'prefix': 'Adams'},
    'Cumberland County': {'p': 1, 'prefix': 'Cumberland'},
}

# =====================================================================
# 1. Data Loading
# =====================================================================
def load_instance(prefix, inst_id, max_n=N_CUSTOMERS):
    """Return (n_customers, D_drive_dict, W_walk_dict)."""
    base = DATA_DIR
    target_nodes = set(range(max_n + 1)) # 0 to max_n

    # --- coordinates (node 0 = depot, 1..n = customers) ---
    # We just need to know if max_n is available. The CSV has 50.
    n = max_n

    # --- driving time matrix (0..n x 0..n) in minutes ---
    D = {}
    with open(os.path.join(base, f"{prefix}_{inst_id}_Driving.csv"), "r") as f:
        for row in csv.DictReader(f):
            key = ast.literal_eval(row["key"])
            if key[0] in target_nodes and key[1] in target_nodes:
                D[key] = float(row["Time"])

    # --- walking time matrix (1..n x 1..n) in minutes ---
    W = {}
    with open(os.path.join(base, f"{prefix}_{inst_id}_Walking.csv"), "r") as f:
        for row in csv.DictReader(f):
            key = ast.literal_eval(row["key"])
            if key[0] in target_nodes and key[1] in target_nodes:
                W[key] = float(row["Time"])

    return n, D, W

# =====================================================================
# 2. Walk service-time for a service set
# =====================================================================
BIG = 99999.0

def walk_service_time(park, sset, W):
    """Minimum round-trip walk time from `park` through customers in
    `sset` and back.  Tries all permutations (|sset| <= q <= 3)."""
    if not sset:
        return 0.0
    if len(sset) == 1:
        c = sset[0]
        return W.get((park, c), BIG) + W.get((c, park), BIG)
    best = BIG
    for perm in itertools.permutations(sset):
        t = W.get((park, perm[0]), BIG)
        for i in range(len(perm) - 1):
            t += W.get((perm[i], perm[i + 1]), BIG)
        t += W.get((perm[-1], park), BIG)
        best = min(best, t)
    return best

# =====================================================================
# 3. TSP Solver (MTZ formulation via Gurobi)
# =====================================================================
def solve_tsp(locations, D, time_limit=120):
    """Return cost of optimal TSP tour on `locations` using driving
    times `D`.  Node 0 is the depot (must be in locations)."""
    locs = list(locations)
    if len(locs) <= 1:
        return 0.0
    if len(locs) == 2:
        a, b = locs
        return D.get((a, b), BIG) + D.get((b, a), BIG)

    m = gp.Model("TSP")
    m.Params.LogToConsole = 0
    m.Params.TimeLimit = time_limit

    pairs = [(i, j) for i in locs for j in locs if i != j]
    x = m.addVars(pairs, vtype=GRB.BINARY)
    u = m.addVars(locs, vtype=GRB.CONTINUOUS)

    m.setObjective(
        gp.quicksum(x[i, j] * D.get((i, j), BIG) for i, j in pairs),
        GRB.MINIMIZE,
    )
    for i in locs:
        m.addConstr(gp.quicksum(x[i, j] for j in locs if j != i) == 1)
        m.addConstr(gp.quicksum(x[j, i] for j in locs if j != i) == 1)

    non_depot = [l for l in locs if l != 0]
    N = len(locs)
    for i in non_depot:
        for j in non_depot:
            if i != j:
                m.addConstr(u[i] - u[j] + N * x[i, j] <= N - 1)

    m.optimize()
    if m.status in (GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SUBOPTIMAL):
        return m.ObjVal
    return BIG


def solve_tsp_tour(locations, D, time_limit=120):
    """Return (cost, tour_list) of TSP on `locations`.
    `tour_list` starts with depot 0."""
    locs = list(locations)
    if len(locs) <= 1:
        return 0.0, locs
    if len(locs) == 2:
        a, b = locs
        return D.get((a, b), BIG) + D.get((b, a), BIG), locs

    m = gp.Model("TSP_tour")
    m.Params.LogToConsole = 0
    m.Params.TimeLimit = time_limit

    pairs = [(i, j) for i in locs for j in locs if i != j]
    x = m.addVars(pairs, vtype=GRB.BINARY)
    u = m.addVars(locs, vtype=GRB.CONTINUOUS)

    m.setObjective(
        gp.quicksum(x[i, j] * D.get((i, j), BIG) for i, j in pairs),
        GRB.MINIMIZE,
    )
    for i in locs:
        m.addConstr(gp.quicksum(x[i, j] for j in locs if j != i) == 1)
        m.addConstr(gp.quicksum(x[j, i] for j in locs if j != i) == 1)

    non_depot = [l for l in locs if l != 0]
    N = len(locs)
    for i in non_depot:
        for j in non_depot:
            if i != j:
                m.addConstr(u[i] - u[j] + N * x[i, j] <= N - 1)

    m.optimize()
    if m.status not in (GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SUBOPTIMAL):
        return BIG, locs

    # extract ordered tour starting from depot
    tour = [0]
    visited = {0}
    cur = 0
    for _ in range(len(locs) - 1):
        for j in locs:
            if j not in visited and x[cur, j].X > 0.5:
                tour.append(j)
                visited.add(j)
                cur = j
                break
    return m.ObjVal, tour

# =====================================================================
# 4. PA-R (Parking Assignment) — core of the CDPP heuristic
# =====================================================================
def solve_PAR(C, W, p_cost, walk_weight=1.0, time_limit=300):
    """Facility-location model (Eq. 13-18 in the paper).

    Parameters
    ----------
    C          : list of customer node ids [1..n]
    W          : walking time dict  (i,k) -> minutes
    p_cost     : opening cost per parking spot (p_time for CDPP,
                 proxy value for Relaxed M-S)
    walk_weight: multiplier on walking assignment cost (1.0 for CDPP,
                 (1-alpha) for Relaxed M-S proxy)
    Returns  (parked_locs, assigned_dict)
    """
    m = gp.Model("PAR")
    m.Params.LogToConsole = 0
    m.Params.TimeLimit = time_limit

    p_var = m.addVars(C, vtype=GRB.BINARY)
    a_var = m.addVars([(i, k) for i in C for k in C], vtype=GRB.BINARY)

    m.setObjective(
        gp.quicksum(p_cost * p_var[i] for i in C)
        + gp.quicksum(
            walk_weight * W.get((i, k), BIG) * a_var[i, k]
            for i in C for k in C
        ),
        GRB.MINIMIZE,
    )

    # each customer -> exactly one parking spot
    for k in C:
        m.addConstr(gp.quicksum(a_var[i, k] for i in C) == 1)
    # assignment => parking spot open
    for i in C:
        for k in C:
            m.addConstr(a_var[i, k] <= p_var[i])
    # open => at least one customer
    for i in C:
        m.addConstr(p_var[i] <= gp.quicksum(a_var[i, k] for k in C))

    m.optimize()
    if m.status not in (GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SUBOPTIMAL):
        # fallback: every customer is its own parking spot
        parked = list(C)
        assigned = {i: [i] for i in C}
        return parked, assigned

    parked = [i for i in C if p_var[i].X > 0.5]
    assigned = {
        i: [k for k in C if a_var[i, k].X > 0.5]
        for i in parked
    }
    return parked, assigned

# =====================================================================
# 5. SSA (Service Set Assignment) for a single parking spot
# =====================================================================
def solve_SSA(park, customers, W, q=Q_CAP, f=F_TIME):
    """Return total (walking + loading) time for serving `customers`
    from parking spot `park`.  Paper Eq. (19)-(21)."""
    if not customers:
        return 0.0
    if len(customers) == 1:
        c = customers[0]
        wt = W.get((park, c), 0.0) + W.get((c, park), 0.0) + f
        return wt

    # generate all subsets of size <= q
    S = []
    for r in range(1, min(q, len(customers)) + 1):
        S.extend(list(itertools.combinations(customers, r)))

    # walking + loading time for each service set
    wt = {}
    for j, ss in enumerate(S):
        wt[j] = walk_service_time(park, list(ss), W) + f * len(ss)

    # set-partitioning MIP
    m = gp.Model("SSA")
    m.Params.LogToConsole = 0
    y = m.addVars(len(S), vtype=GRB.BINARY)
    m.setObjective(
        gp.quicksum(wt[j] * y[j] for j in range(len(S))),
        GRB.MINIMIZE,
    )
    for k in customers:
        Jk = [j for j, ss in enumerate(S) if k in ss]
        m.addConstr(gp.quicksum(y[j] for j in Jk) == 1)

    m.optimize()
    return m.ObjVal if m.status in (GRB.OPTIMAL,) else sum(
        wt[j] for j in range(len(S)) if len(S[j]) == 1
    )

# =====================================================================
# 6. CDPP Heuristic  (PA-R -> SSA -> TSP on parking spots)
# =====================================================================
def run_cdpp_heuristic(n, D, W, p_time, q=Q_CAP, f=F_TIME):
    """Two-echelon location-routing heuristic (Section 3.3).
    Returns: completion_time (minutes)."""
    C = list(range(1, n + 1))

    # Stage 1 — Parking Assignment
    parked, assigned = solve_PAR(C, W, p_cost=p_time, walk_weight=1.0)

    # Stage 2 — Service Set Assignment for each parking spot
    total_wl = 0.0
    for pk in parked:
        custs = assigned.get(pk, [])
        if custs:
            total_wl += solve_SSA(pk, custs, W, q, f)

    # TSP on parking spots + depot
    drive = solve_tsp([0] + parked, D, time_limit=120)

    # parking penalty
    park_penalty = len(parked) * p_time

    return drive + park_penalty + total_wl

# =====================================================================
# 7. TSP Baseline  (= Relaxed M-S  alpha = 0.5)
# =====================================================================
def run_tsp_baseline(n, D, p_time, f=F_TIME, tsp_cost=None):
    """Park at every customer.  Equivalent to CDPP with p=0.
    completion = TSP_drive + n*p + n*f"""
    if tsp_cost is None:
        C = list(range(1, n + 1))
        tsp_cost = solve_tsp([0] + C, D, time_limit=300)
    return tsp_cost + n * p_time + n * f

# =====================================================================
# 8. Modified TSP  (route-first cluster-second, Section 5.2.1)
# =====================================================================
def run_modified_tsp(n, D, W, p_time, q=Q_CAP, f=F_TIME, tour=None):
    """Fix customer order from TSP, then DP to decide optimal
    parking/walking clusters along that order."""
    C = list(range(1, n + 1))

    # Step 1: get TSP tour  (shared computation)
    if tour is None:
        _, tour = solve_tsp_tour([0] + C, D, time_limit=300)
    cust_order = [c for c in tour if c != 0]

    # Step 2: DP along fixed order
    # dp[i] = min cost to serve first i customers in cust_order
    INF = float('inf')
    MAX_GROUP = min(n, 15)     # practial limit on group size
    dp_cost = [INF] * (n + 1)
    dp_park = [0] * (n + 1)   # last parking location
    dp_cost[0] = 0.0           # vehicle at depot

    def group_walk_load(park, group):
        """Walk+load for serving consecutive `group` from `park`,
        maintaining TSP order.  Multiple trips of <= q."""
        total = 0.0
        for ts in range(0, len(group), q):
            trip = group[ts:ts + q]
            wt = W.get((park, trip[0]), 0.0)
            for k in range(len(trip) - 1):
                wt += W.get((trip[k], trip[k + 1]), 0.0)
            wt += W.get((trip[-1], park), 0.0)
            total += wt + f * len(trip)
        return total

    for i in range(1, n + 1):
        for gs in range(max(0, i - MAX_GROUP), i):
            if dp_cost[gs] >= INF:
                continue
            group = cust_order[gs:i]
            park_loc = group[0]            # park at first in group
            prev_park = dp_park[gs]

            cost = (
                dp_cost[gs]
                + D.get((prev_park, park_loc), BIG)    # drive
                + p_time                               # parking
                + group_walk_load(park_loc, group)      # walk + load
            )
            if cost < dp_cost[i]:
                dp_cost[i] = cost
                dp_park[i] = park_loc

    # drive back to depot
    return dp_cost[n] + D.get((dp_park[n], 0), 0.0)

# =====================================================================
# 9. Relaxed M-S  alpha = 0.6 / 0.8  (proxy via modified PA-R)
# =====================================================================
def run_relaxed_ms(n, D, W, p_actual, alpha, q=Q_CAP, f=F_TIME):
    """Proxy for Relaxed M-S benchmark.

    Key idea (paper Eq. 23):
      Relaxed M-S optimizes  alpha*driving + (1-alpha)*walking  (no
      parking in objective). The solution is then evaluated with the
      actual completion time  (driving + walking + loading + s*p).

    Since the PA-R doesn't model driving directly, we add a surrogate
    opening cost = alpha * avg_nearest_neighbor_driving_time to capture
    the effect of alpha on parking consolidation.
    """
    C = list(range(1, n + 1))

    # estimate avg nearest-neighbor driving time
    nn_drives = []
    for i in C:
        dists = [D.get((i, j), BIG) for j in C if j != i and D.get((i, j), BIG) < BIG]
        if dists:
            nn_drives.append(min(dists))
    avg_nn = float(np.mean(nn_drives)) if nn_drives else 2.0

    # PA-R with proxy costs
    p_proxy = alpha * avg_nn           # opening cost
    ww = 1.0 - alpha                   # walking weight

    parked, assigned = solve_PAR(C, W, p_cost=p_proxy, walk_weight=ww)

    # SSA (with real walking + loading times)
    total_wl = 0.0
    for pk in parked:
        custs = assigned.get(pk, [])
        if custs:
            total_wl += solve_SSA(pk, custs, W, q, f)

    # TSP on parking spots
    drive = solve_tsp([0] + parked, D, time_limit=120)

    # ACTUAL completion time with REAL parking penalty
    park_penalty = len(parked) * p_actual
    return drive + park_penalty + total_wl

# =====================================================================
# 10. Main — run experiments and plot Figure 3
# =====================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("Reproducing Figure 3 — Does Parking Matter?")
    print("Base case: n=50, q=%d, f=%.1f min" % (Q_CAP, F_TIME))
    print("Instances per county: %d" % N_INSTANCES)
    print("=" * 70)

    counties_list = list(COUNTIES.keys())

    # storage: county -> method -> [values per instance]
    results = {
        c: {
            'cdpp': [], 'tsp': [],
            'rms_05': [], 'rms_06': [], 'rms_08': [],
            'mod_tsp': [],
        }
        for c in counties_list
    }

    for county_name in counties_list:
        cfg = COUNTIES[county_name]
        prefix = cfg['prefix']
        p = cfg['p']

        print(f"\n{'='*60}")
        print(f"  {county_name}  (p = {p} min)")
        print(f"{'='*60}")

        for inst in range(1, N_INSTANCES + 1):
            t0 = time_mod.time()
            print(f"  Instance {inst:2d}/{N_INSTANCES} ... ", end="", flush=True)

            # ---- load data -------------------------------------------------
            n, D, W = load_instance(prefix, inst)

            # ---- shared: TSP on all customers (used by baseline & ModTSP) --
            C = list(range(1, n + 1))
            tsp_cost, tsp_tour = solve_tsp_tour([0] + C, D, time_limit=300)

            # ---- 1. CDPP heuristic -----------------------------------------
            cdpp = run_cdpp_heuristic(n, D, W, p)
            results[county_name]['cdpp'].append(cdpp)

            # ---- 2. TSP baseline (= Relaxed M-S alpha=0.5) ----------------
            tsp_base = run_tsp_baseline(n, D, p, tsp_cost=tsp_cost)
            results[county_name]['tsp'].append(tsp_base)
            results[county_name]['rms_05'].append(tsp_base)

            # ---- 3. Relaxed M-S alpha = 0.6 --------------------------------
            rms06 = run_relaxed_ms(n, D, W, p, alpha=0.6)
            results[county_name]['rms_06'].append(rms06)

            # ---- 4. Relaxed M-S alpha = 0.8 --------------------------------
            rms08 = run_relaxed_ms(n, D, W, p, alpha=0.8)
            results[county_name]['rms_08'].append(rms08)

            # ---- 5. Modified TSP -------------------------------------------
            mod = run_modified_tsp(n, D, W, p, tour=tsp_tour)
            results[county_name]['mod_tsp'].append(mod)

            dt = time_mod.time() - t0
            print(
                f"done  ({dt:5.1f}s) | "
                f"CDPP={cdpp:7.1f}  TSP={tsp_base:7.1f}  "
                f"RMS08={rms08:7.1f}  ModTSP={mod:7.1f}"
            )

    # =================================================================
    # Compute average percent reductions
    # =================================================================
    print("\n" + "=" * 70)
    print("  Percent reduction in completion time  (CDPP vs benchmarks)")
    print("=" * 70)

    benchmarks = [
        (r'Relaxed M-S ($\alpha=0.5$)', 'rms_05'),
        (r'Relaxed M-S ($\alpha=0.6$)', 'rms_06'),
        (r'Relaxed M-S ($\alpha=0.8$)', 'rms_08'),
        ('Modified TSP',                'mod_tsp'),
    ]

    savings = {}
    for label, key in benchmarks:
        vals = []
        for county in counties_list:
            cdpp_vals  = results[county]['cdpp']
            bench_vals = results[county][key]
            # percent reduction = (bench - cdpp) / bench * 100
            pcts = [
                100.0 * (b - c) / b
                for c, b in zip(cdpp_vals, bench_vals)
                if b > 0
            ]
            avg = float(np.mean(pcts)) if pcts else 0.0
            vals.append(avg)
        savings[label] = vals
        print(f"  {label:40s}  "
              + "  ".join(f"{v:6.1f}%" for v in vals))

    # =================================================================
    # Plot Figure 3
    # =================================================================
    x = np.arange(len(counties_list))
    width = 0.18
    offsets = [-1.5, -0.5, 0.5, 1.5]
    colors = ['#4e79a7', '#59a14f', '#f28e2b', '#e15759']

    fig, ax = plt.subplots(figsize=(10, 6))
    for idx, (label, vals) in enumerate(savings.items()):
        rects = ax.bar(
            x + offsets[idx] * width, vals, width,
            label=label, color=colors[idx],
        )
        for rect in rects:
            h = rect.get_height()
            ax.annotate(
                f'{h:.1f}%',
                xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3),
                textcoords='offset points',
                ha='center', va='bottom', fontsize=8,
            )

    ax.set_ylabel('Percent Reduction in Completion Time (%)', fontsize=12)
    ax.set_title(
        'Fig. 3  Average percent reduction in completion time\n'
        r'by using CDPP relative to benchmarks (base case: '
        r'$n{=}50,\; q{=}3,\; f{=}2.1$ min)',
        fontsize=11, pad=12,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(counties_list, fontsize=11)
    ymax = max(max(v) for v in savings.values()) if savings else 60
    ax.set_ylim(0, ymax * 1.25)
    ax.legend(loc='upper right', fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, linestyle='--', alpha=0.4)

    plt.tight_layout()
    out_path = os.path.join(os.path.dirname(__file__), 'fig3_reproduced.png')
    plt.savefig(out_path, dpi=300)
    print(f"\nSaved chart: {out_path}")
    plt.show()
