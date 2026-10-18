import json, math
from collections import defaultdict

d = json.load(open("places.json"))
items = d["places"]

print("TOTAL:", len(items))

# 1) exact name dupes
by_name = defaultdict(list)
for p in items:
    by_name[p["name"]].append(p)
print("\n== EXACT NAME DUPLICATES ==")
for n, ps in by_name.items():
    if len(ps) > 1:
        print("DUP:", n, [p["id"] for p in ps])

# 2) normalized name dupes
import re
def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower())
by_norm = defaultdict(list)
for p in items:
    by_norm[norm(p["name"])].append(p)
print("\n== NORMALIZED NAME DUPLICATES ==")
for n, ps in by_norm.items():
    if len(ps) > 1:
        print("DUP:", [(p["id"], p["name"]) for p in ps])

# 3) proximity < 200m
print("\n== PROXIMITY < 200m ==")
valid = [p for p in items if p.get("lat") is not None and p.get("lng") is not None]
for i in range(len(valid)):
    for j in range(i+1, len(valid)):
        a, b = valid[i], valid[j]
        dlat = (a["lat"] - b["lat"]) * 111320
        dlng = (a["lng"] - b["lng"]) * 111320 * math.cos(math.radians(a["lat"]))
        dist = math.hypot(dlat, dlng)
        if dist < 200:
            print("%.0fm: [%s] %r <-> [%s] %r (%s)" % (dist, a["id"], a["name"], b["id"], b["name"], a.get("regionId")))

# 4) the two masjid jami entries
print("\n== MASJID JAMI ENTRIES ==")
for p in items:
    if "masjid jami" in p["name"].lower():
        print(json.dumps(p, ensure_ascii=False, indent=2))
