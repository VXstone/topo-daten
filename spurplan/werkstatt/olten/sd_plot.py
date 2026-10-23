import runpy, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
st = sys.argv[1]; sys.argv = ['x', '--src', st + '.json', '--nowarp']
g = runpy.run_path('spurplan_schema.py')
SD = g['SD']; fig, ax = plt.subplots(figsize=(20, 7))
for w in g['ways'].values():
    p = [SD[n] for n in w['nodes']]; t = w['tags']
    c = '0.6' if t.get('service') in ('yard', 'spur') else ('orange' if t.get('service') else 'g')
    ax.plot([q[0] for q in p], [q[1] for q in p], c, lw=1.5)
    if t.get('railway:track_ref'): ax.text(p[len(p)//2][0], p[len(p)//2][1], t['railway:track_ref'], fontsize=8, color='m')
for n, t in g['ntag'].items():
    if n in SD and t.get('railway') == 'switch': ax.plot(*SD[n], 'r.', ms=4)
ax.axvline(g['CFG']['s_min'], color='b'); ax.axvline(g['CFG']['s_max'], color='b')
ax.axhline(g['d_lim_at'](0), color='b', ls=':'); ax.axhline(-g['d_lim_at'](0), color='b', ls=':')
ax.set_ylim(-150, 150); ax.set_xlim(g['CFG']['s_min'] - 600, g['CFG']['s_max'] + 600)
plt.savefig(st + '_sd.png', dpi=50, bbox_inches='tight')
