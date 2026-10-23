"""
x-Entzerrung: findet eine monotone Abbildung s -> x, sodass jede Verbindung
genau den Platz der Standardgeometrie (60°, Radius) bekommt, und der Plan sonst
möglichst massstäblich bleibt.  Lineares Programm (HiGHS).
  min  Σ w_r·(Breite_r)  +  ε·Σ |Δx_i − Δs_i·k|
  u.d.N.  Breite_r ≥ Standardbreite_r,   Δx_i ≥ 0.15·Δs_i·k
"""
import json, sys, numpy as np
KEY = sys.argv[1] if len(sys.argv) > 1 else ""
PFX = KEY + "_" if KEY else ""
from scipy.optimize import linprog
R = json.load(open(PFX + "req.json"))
k = R["px_per_m"]
knots = sorted(set([R["s_min"], R["s_max"]] + [a for a, b, w, _ in R["req"]] + [b for a, b, w, _ in R["req"]]))
ks = [knots[0]]
for v in knots[1:]:
    if v - ks[-1] > 0.3: ks.append(v)
ks = np.array(ks); n = len(ks) - 1
base = np.diff(ks) * k
idx = lambda v: int(np.argmin(np.abs(ks - v)))
EPS = 0.08
# Variablen: d (n), u (n)
c = np.r_[np.zeros(n), EPS * np.ones(n)]
A, b = [], []
for a_, b_, wpx, wt in R["req"]:
    i, j = idx(a_), idx(b_)
    if j <= i: continue
    row = np.zeros(2 * n); row[i:j] = -1; A.append(row); b.append(-wpx)      # Breite >= Standard
    if wt > 0: c[i:j] += wt * (1.0 if base[i:j].sum() < 4 * wpx else 0.15)             # lange Verbindungen: nicht stauchen
for i in range(n):
    r1 = np.zeros(2 * n); r1[i] = 1; r1[n + i] = -1; A.append(r1); b.append(base[i])
    r2 = np.zeros(2 * n); r2[i] = -1; r2[n + i] = -1; A.append(r2); b.append(-base[i])
WMIN = R.get("warp_min", 0.15)      # cfg.warp_min: Mindestanteil des Massstabs (Rothrist regional 20.10.: nicht stauchen)
bounds = [(WMIN * base[i], None) for i in range(n)] + [(0, None)] * n
res = linprog(c, A_ub=np.array(A), b_ub=np.array(b), bounds=bounds, method="highs")
print(res.message)
x = np.r_[0, np.cumsum(res.x[:n])]
json.dump(dict(s=ks.tolist(), x=x.tolist()), open(PFX + "warp.json", "w"))
print("Breite linear %.0f px -> entzerrt %.0f px" % (base.sum(), x[-1]))
