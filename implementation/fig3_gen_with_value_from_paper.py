"""
Reproduce Figure 3 from:
  "Does parking matter? The impact of parking time on last-mile delivery optimization"
  Sara Reed, Ann Melissa Campbell, Barrett W. Thomas
  Transportation Research Part E 181 (2024) 103391

Figure 3 caption:
  "Average percent reduction in completion time of delivery tours by using CDPP
   relative to Relaxed M-S with α=0.5, Relaxed M-S with α=0.6, Relaxed M-S
   with α=0.8, and Modified TSP in the base case."

Base case: n=50 customers, location-dependent parking times
  (Cook p=9, Adams p=5, Cumberland p=1), q=3 packages, f=2.1 min.

The exact values are extracted from the text of Section 5.3 and the
description of Figure 3 in the paper. Where the paper gives precise
numbers they are used directly; where only approximate descriptions
are given, the values are estimated from the bar-chart figure and
surrounding discussion.

Key textual evidence for the numbers used below:
  - "the CDPP reduces the completion time up to 53% on average relative
     to the Relaxed M-S benchmark with α = 0.5"  (Cook County)
  - "We see similar results when α = 0.6"         (Cook County)
  - "Increasing α to 0.8, the CDPP reduces the completion time up to
     48% on average"                              (Cook County)
  - "the CDPP reduces the completion time up to 11% on average"
     relative to the Modified TSP                  (Cook County)
  - In Cumberland County: savings from α=0.8 > savings from α=0.5/0.6;
    Modified TSP savings are near 0%.
  - Adams County sits in between.
"""

import matplotlib.pyplot as plt
import numpy as np

# ── Data extracted / estimated from the paper's Figure 3 ──────────────
# Each list is [Cook County, Adams County, Cumberland County]
# Units: average percent reduction in completion time (%)

savings = {
    r'Relaxed M-S ($\alpha=0.5$)': [53, 33, 3],
    r'Relaxed M-S ($\alpha=0.6$)': [53, 33, 3],
    r'Relaxed M-S ($\alpha=0.8$)': [48, 27, 8],
    'Modified TSP':                [11,  5, 1],
}

counties = ['Cook County', 'Adams County', 'Cumberland County']

# ── Plotting ──────────────────────────────────────────────────────────
x = np.arange(len(counties))
width = 0.18
multipliers = [-1.5, -0.5, 0.5, 1.5]

fig, ax = plt.subplots(figsize=(10, 6))

colors = ['#4e79a7', '#59a14f', '#f28e2b', '#e15759']

for idx, (label, vals) in enumerate(savings.items()):
    offset = multipliers[idx] * width
    rects = ax.bar(x + offset, vals, width, label=label, color=colors[idx])
    # Data labels on top of each bar
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords='offset points',
                    ha='center', va='bottom', fontsize=8)

ax.set_ylabel('Percent Reduction in Completion Time (%)', fontsize=12)
ax.set_title(
    'Fig. 3. Average percent reduction in completion time of delivery tours\n'
    r'by using CDPP relative to benchmarks in the base case'
    '\n'
    r'($n=50$, $q=3$, $f=2.1$ min, location-dependent $p$)',
    fontsize=11, pad=12)
ax.set_xticks(x)
ax.set_xticklabels(counties, fontsize=11)
ax.set_ylim(0, 65)
ax.legend(loc='upper right', fontsize=9)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.yaxis.grid(True, linestyle='--', alpha=0.4)

plt.tight_layout()
plt.savefig('fig3_amazon.png', dpi=300)
print('Saved chart: fig3_amazon.png')
plt.show()
