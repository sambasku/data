#!/usr/bin/env python3
import json, requests, sys, re
from collections import defaultdict

def geocode(name, region):
    q = f"{name} {region}"
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": q, "format": "json", "limit": 1, "addressdetails": 1}
    headers = {"User-Agent": "sambasku-data-fix/1.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None, None, "no result"
        first = data[0]
        lat = float(first.get("lat"))
        lon = float(first.get("lon"))
        return lat, lon, "ok"
    except Exception as e:
        return None, None, str(e)

def main():
    path = "/Users/ibnulmutaki/Development/github/sambasku/data/places.json"
    d = json.load(open(path))
    items = d["places"]
    targets = [
        {"id": "rumah-tahanan-belanda", "name": "Rumah Tahanan Belanda", "region": "pemangkat"},
        {"id": "pantai-tanjung-kemuning", "name": "Pantai Tanjung Kemuning", "region": "paloh"},
        {"id": "pantai-tanjung-bendera", "name": "Pantai Tanjung Bendera", "region": "paloh"},
        {"id": "pantai-tanjung-api", "name": "Pantai Tanjung Api", "region": "paloh"},
        {"id": "pantai-polaria", "name": "Pantai Polaria", "region": "selakau"},
        {"id": "makam-ratu-sepudak", "name": "Makam Ratu Sepudak", "region": "galing"},
        {"id": "makamsyech-muhammad-sattaruddin", "name": "MakamSyech Muhammad Sattaruddin", "region": "galing"},
        {"id": "makam-keramat-dato-sanggup", "name": "Makam Keramat Dato' Sanggup", "region": "galing"},
    ]
    updates = []
    for t in targets:
        p = next((x for x in items if x["id"] == t["id"]), None)
        if not p:
            print(f"SKIP: {t['id']} not found")
            continue
        old_lat, old_lon = p.get("lat"), p.get("lng")
        lat, lon, err = geocode(t["name"], t["region"])
        if err:
            print(f"FAIL {t['id']} {t['name']} ({t['region']}): {err}")
            continue
        if old_lat == lat and old_lon == lon:
            print(f"SKIP {t['id']} {t['name']} - same coords")
            continue
        p["lat"] = lat
        p["lng"] = lon
        updates.append({
            "id": t["id"],
            "name": t["name"],
            "old": (old_lat, old_lon),
            "new": (lat, lon),
        })
        print(f"UPDATED {t['id']} {t['name']} -> {lat}, {lon}")

    if updates:
        print("\n=== SUMMARY ===")
        for u in updates:
            print(f"{u['id']} {u['name']}: {u['old']} -> {u['new']}")
        print("\nSaving...")
        json.dump(d, open(path, "w"), ensure_ascii=False, indent=2)
        print("Saved. Now commit & push.")
        # commit
        import subprocess
        subprocess.run(["git", "add", path], check=True)
        subprocess.run(["git", "commit", "-m", f"fix: re-geocode 8 places (fix #152)"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("Pushed to origin/main")
    else:
        print("No updates needed.")

if __name__ == "__main__":
    main()