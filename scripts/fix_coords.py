#!/usr/bin/env python3
"""Re-geocode 8 places dengan koordinat fallback salah (issue #152).

Sumber: Nominatim OpenStreetMap. Guard: hasil harus di bounding box
Kabupaten Sambas (lat 0.8-2.1, lng 108.8-109.7) — buang hasil salah sasaran.
Tidak mengubah file bila tidak ada update. Commit manual setelah review.
"""
import json
import time
import urllib.parse
import urllib.request

PATH = "/Users/ibnulmutaki/Development/github/sambasku/data/places.json"
# Bounding box Kabupaten Sambas (longgar, termasuk Paloh di utara)
LAT_MIN, LAT_MAX = 0.8, 2.1
LNG_MIN, LNG_MAX = 108.8, 109.7

TARGETS = [
    {"id": "rumah-tahanan-belanda", "q": "Rumah Tahanan Belanda, Pemangkat, Sambas"},
    {"id": "pantai-tanjung-kemuning", "q": "Pantai Tanjung Kemuning, Paloh, Sambas"},
    {"id": "pantai-tanjung-bendera", "q": "Pantai Tanjung Bendera, Paloh, Sambas"},
    {"id": "pantai-tanjung-api", "q": "Pantai Tanjung Api, Paloh, Sambas"},
    {"id": "pantai-polaria", "q": "Pantai Polaria, Selakau, Sambas"},
    {"id": "makam-ratu-sepudak", "q": "Makam Ratu Sepudak, Galing, Sambas"},
    {"id": "makamsyech-muhammad-sattaruddin", "q": "Makam Syech Muhammad Sattaruddin, Galing, Sambas"},
    {"id": "makam-keramat-dato-sanggup", "q": "Makam Keramat Dato Sanggup, Galing, Sambas"},
]


def geocode(query):
    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": 3})
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "sambasku-data-fix/1.0 (github.com/sambasku)"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def in_bbox(lat, lng):
    return LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX


def main():
    d = json.load(open(PATH))
    items = d["places"]
    updates = []
    for t in TARGETS:
        p = next((x for x in items if x["id"] == t["id"]), None)
        if not p:
            print(f"SKIP  {t['id']}: tidak ada di places.json")
            continue
        try:
            results = geocode(t["q"])
        except Exception as e:
            print(f"FAIL  {t['id']}: {e}")
            time.sleep(1.1)
            continue
        hit = next((r for r in results
                    if in_bbox(float(r["lat"]), float(r["lon"]))), None)
        if not hit:
            print(f"NOHIT {t['id']} {p['name']!r}: {len(results)} hasil, semua di luar bbox Sambas")
            time.sleep(1.1)
            continue
        lat, lng = float(hit["lat"]), float(hit["lon"])
        if abs(lat - p["lat"]) < 1e-6 and abs(lng - p["lng"]) < 1e-6:
            print(f"SAME  {t['id']}")
            time.sleep(1.1)
            continue
        old = (p["lat"], p["lng"])
        p["lat"] = lat
        p["lng"] = lng
        updates.append({"id": t["id"], "name": p["name"], "old": old, "new": (lat, lng),
                        "display": hit.get("display_name", "")[:80]})
        print(f"OK    {t['id']}: {old} -> ({lat}, {lng}) | {hit.get('display_name', '')[:60]}")
        time.sleep(1.1)  # rate limit Nominatim

    if updates:
        json.dump(d, open(PATH, "w"), ensure_ascii=False, indent=2)
        print(f"\n{len(updates)} entri di-update di places.json (BELUM di-commit).")
    else:
        print("\nTidak ada update tersimpan.")


if __name__ == "__main__":
    main()
