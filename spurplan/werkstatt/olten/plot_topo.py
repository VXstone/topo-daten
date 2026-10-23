import json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
T = json.load(open(sys.argv[1]))
fig, ax = plt.subplots(figsize=(14, 16))
col = {1: 'tab:blue', 2: 'tab:green', 3: 'tab:orange', 4: 'tab:red'}
for e in T['edges']:
    g = e['geom']; ax.plot([p[0] for p in g], [p[1] for p in g], color=col[e['tracks']], lw=1 + e['tracks'])
    m = g[len(g)//2]; ax.text(m[0], m[1], '/'.join(e['refs']), fontsize=7, color='0.4')
mk = {'station': 'ks', 'halt': 'ko', 'junction': 'r^', 'end': 'mx', 'exit': 'b>'}
for n in T['nodes']:
    ax.plot(n['x'], n['y'], mk[n['kind']], ms=7)
    ax.text(n['x'] + 80, n['y'], f"{n['id']} {n['name']}", fontsize=8)
ax.set_aspect(1); plt.savefig(sys.argv[2], dpi=55, bbox_inches='tight')
