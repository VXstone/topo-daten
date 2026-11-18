import math
G="#00862f"; K="#111"; T=math.tan(math.radians(60))
out=[]
def rpath(pts, r=7):
    """Polylinie mit ausgerundeten Ecken (Quadratische Bögen)."""
    d=f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1,len(pts)-1):
        p,q,n=pts[i-1],pts[i],pts[i+1]
        a=math.dist(p,q); b=math.dist(q,n); rr=min(r,a/2,b/2)
        s=(q[0]+(p[0]-q[0])*rr/a, q[1]+(p[1]-q[1])*rr/a); e=(q[0]+(n[0]-q[0])*rr/b, q[1]+(n[1]-q[1])*rr/b)
        d+=f"L{s[0]:.1f},{s[1]:.1f}Q{q[0]:.1f},{q[1]:.1f} {e[0]:.1f},{e[1]:.1f}"
    d+=f"L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"; return d
def gleis(pts,haupt=True):
    out.append(f'<path d="{rpath(pts)}" fill="none" stroke="{G if haupt else K}" stroke-width="{3.6 if haupt else 1.5}" stroke-linecap="round"/>')
def diag(x0,y0,y1,links=True):  # 60°-Diagonale von (x0,y0) nach Ebene y1, Richtung links/rechts
    dx=abs(y1-y0)/T; return (x0-dx if links else x0+dx, y1)
def prell(x,y): out.append(f'<circle cx="{x}" cy="{y}" r="2.6" fill="{K}"/>')
def perron(x0,x1,y): out.append(f'<rect x="{x0}" y="{y-3}" width="{x1-x0}" height="6" rx="1.5" fill="{G}"/>')
def nr(t,x,y): out.append(f'<rect x="{x-9}" y="{y-8}" width="18" height="16" fill="#fff"/><text x="{x}" y="{y+5}" font-size="14" font-weight="600" text-anchor="middle" fill="{G}">{t}</text>')
def txt(t,x,y,size=13,anchor="middle",w=600,col=G): out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" text-anchor="{anchor}" fill="{col}">{t}</text>')
def pfeil(x,y,rechts,l1,l2,col=G):
    s=1 if rechts else -1; xa=x+s*14; sw=3.6 if col==G else 1.5
    out.append(f'<path d="M{x},{y}H{xa}" stroke="{col}" stroke-width="{sw}"/><path d="M{xa},{y-5}L{xa+s*9},{y}L{xa},{y+5}Z" fill="{col}"/>')
    an="start" if rechts else "end"; tx=xa+s*14
    txt(l1,tx,y-3,12,an,600,col); txt(l2,tx,y+12,12,an,500,col)

B,A=300,324
d=12/(math.sqrt(3)/2)          # Gleis B (oben, NW-Seite) und A (unten, Perronseite) – Doppelspur Selnau–Giesshübel–Sihltal
XR=1500              # rechter Planrand (Richtung Selnau)
# ---- Doppelspur Richtung Selnau mit Spurwechsel und Schere (Sihlbrücke)
gleis([(XR,B),(880,B)]); gleis([(XR,A),(880+d,A)])
# Knick ins Sihltal (REGELN 2.15: abbiegende Linie als Abzweig, Bündel knickt gemeinsam, Querabstand bleibt – 2.7)
d=12/(math.sqrt(3)/2)               # Knickversatz: gleicher Querabstand nach dem 60°-Knick (REGELN 1.15)
yB2,yA2=396,420
gleis([(880,B),diag(880,B,yB2),(380,yB2)]); gleis([(880+d,A),diag(880+d,A,yA2),(380,yA2)])
# Schere auf der Sihlbrücke und Spurwechsel weiter Richtung Selnau
gleis([(1300+24/T,B),(1300,A)])      # Spurwechsel B->A (OSM: Y s=668 -> X s=735), keine Schere
gleis([(1420,A),(1420-24/T,B)])
# Spurwechsel A->B am SW-Kopf Giesshübel
gleis([(1062,A),(1062-24/T,B)])
# Perron Giesshübel an Gleis A (aussen), Gleisnummer widersprüchlich in OSM -> «?»
perron(1105,1225,A+13); nr("?",1165,A)
# ---- 717 nach Wiedikon (einspurig, mündet in Gleis B), zwei Anschlussgleise
y717=228
gleis([(XR,y717),(1195,y717),diag(1195,y717,B,True)],False)        # 717 nur Güterverkehr -> schwarz (REGELN 1.21)
gleis([(1235,y717),(1235+24/T,204),(1455,204)],False); prell(1455,204)   # Anschlussgleis 41: westlich der 717 (oben)
gleis([(1290,y717),(1290+24/T,252),(1420,252)],False); prell(1420,252)   # Anschlussgleis 43: östlich, zwischen 717 und Hauptgleisen
# ---- 713 nach Binz/Uetliberg: von Gleis B nach oben links
y713=84
gleis([(1140,B),diag(1140,B,y713),(700,y713)])
# ---- Depot: Weichenstrasse ab Gleis B nach oben links, Abstellgleise waagrecht nach links (REGELN 2.3/2.10)
x1,top1=1100,132; gleis([(x1,B),diag(x1,B,top1)],False)          # Anschluss 1 ab B (OSM s=899)
x2=1030; gleis([(x2,B),diag(x2,B,252)],False)                      # Anschluss 2 ab B nach dem Spurwechsel (OSM s=970)
ys=list(range(276,251,-12)); yo=list(range(228,top1-1,-12))
for i,y in enumerate(ys):
    xl=x2-(B-y)/T; xe=640+i*22; gleis([(xl,y),(xe,y)],False); prell(xe,y)
for i,y in enumerate(yo):
    xl=x1-(B-y)/T; xe=706+i*22; gleis([(xl,y),(xe,y)],False); prell(xe,y)
x713=1140-(B-108)/T; gleis([(x713,108),(926,108)],False); prell(926,108)   # Anschluss 3 ab 713 (OSM Knoten -30/-17)
# ---- Saalsporthalle: Spurwechsel B->A davor, Seitenperrons, Spurwechsel dahinter
gleis([(770,yB2),(770-24/T,yA2)])
perron(585,690,yB2-13); perron(585,690,yA2+13); nr("2",637,yB2); nr("1",637,yA2)
gleis([(510,yB2),(510-24/T,yA2)]); gleis([(488,yA2),diag(488,yA2,yA2+24),(395,yA2+24)],False)
# ---- Abgänge
pfeil(XR,B,True,"712","Zürich Selnau – HB"); pfeil(XR,A,True,"",""); 
pfeil(XR,y717,True,"717","Zürich Wiedikon",K)
pfeil(700,y713,False,"713","Binz – Uetliberg"); pfeil(380,yB2,False,"712","Adliswil"); pfeil(380,yA2,False,"","")
# Beschriftung
txt("Zürich Giesshübel",1165,388,22,"middle",700); txt("Depot",860,110,13,"middle",500,K)
txt("Zürich Saalsporthalle",637,478,18,"middle",700)
txt("Zielbild T-SZU2 · Skizze nach REGELN 2.15, Weichenfolge je Hauptgleis aus OSM (Stand 18.11.) · Achse = Einfahrt Selnau + Depot, Sihltal als Abzweig",40,560,12,"start",500,"#666")
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1700 580" font-family="Fira Sans, Arial, sans-serif"><rect width="1700" height="580" fill="#fff"/>{"".join(out)}</svg>'''
open("giesshuebel_ziel.svg","w").write(svg)
import cairosvg; cairosvg.svg2png(bytestring=svg.encode(),write_to="giesshuebel_ziel.png",output_width=2200)
