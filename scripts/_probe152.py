import json, math
from collections import defaultdict, Counter

PATH = "/Users/ibnulmutaki/Development/github/sambasku/data/places.json"
items = json.load(open(PATH))["places"]
print("TOTAL places:", len(items))

# --- 1. sumber ---
print("\n== SUMBER ==")
src = Counter()
for p in items:
    a = (p.get("sources") or [{}])[0].get("address", "") or "?"
    src["opendata(116)" if "opendata.sambas.go.id" in a else ("wikipedia" if "wikipedia" in a else ("sisparnas" if "sisparnas" in a else ("jadesta" if "jadesta" in a else a[:40])))] += 1
for k, v in src.most_common():
    print("  %3d  %s" % (v, k))

# --- 2. kualitas import massal ---
print("\n== KUALITAS ==")
ph = [p for p in items if any("placeholder" in (i.get("url") or "") for i in (p.get("images") or []))]
gen = [p for p in items if (p.get("shortDescription") or "").strip().lower() in ("objek wisata", "", "objek wisata.")]
print("placeholder image :", len(ph))
print("desc generik      :", len(gen))
print("type objek-wisata :", sum(1 for p in items if p.get("type") == "objek-wisata"))
print("tanpa related     :", sum(1 for p in items if not p.get("related")))

# --- 3. koordinat duplikat persis ---
print("\n== KOORDINAT IDENTIK (bug geocode) ==")
by_coord = defaultdict(list)
for p in items:
    if p.get("lat") is None: continue
    by_coord[(round(p["lat"], 5), round(p["lng"], 5))].append(p)
for c, ps in by_coord.items():
    if len(ps) > 1:
        print("  %s :" % (c,))
        for p in ps:
            print("     [%s] %r (%s) src=%s" % (p["id"], p["name"], p.get("regionId"),
                  (p.get("sources") or [{}])[0].get("address", "")[:35]))

# --- 4. kandidat dup nama (token) ---
def toks(s):
    return set(w for w in "".join(c if c.isalnum() or c == " " else " " for c in s.lower()).split() if len(w) > 2)
print("\n== KANDIDAT NAMA KEMBAR ==")
for i in range(len(items)):
    for j in range(i + 1, len(items)):
        a, b = items[i], items[j]
        ta, tb = toks(a["name"]), toks(b["name"])
        if not ta or not tb: continue
        jac = len(ta & tb) / len(ta | tb)
        if jac >= 0.4:
            dist = "-"
            if a.get("lat") and b.get("lat"):
                dlat = (a["lat"] - b["lat"]) * 111320
                dlng = (a["lng"] - b["lng"]) * 111320 * math.cos(math.radians(a["lat"]))
                dist = "%.0fm" % math.hypot(dlat, dlng)
            print("  %-42s <-> %-42s jac=%.2f %s" % (a["name"][:42], b["name"][:42], jac, dist))
            print("      %-42s     %s" % (a["id"], a.get("type")))
            print("      %-42s     %s" % (b["id"], b.get("type")))
