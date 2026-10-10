#!/usr/bin/env python3
"""
Scrape Google Maps share-link (maps.app.goo.gl) for places without mapsUrl.
Uses Playwright Python (headless Chromium) to:
  1. Navigate FRESH to maps.google.com each iteration (avoid stale state)
  2. Search "{name} Kec. {kecamatan} Kabupaten Sambas"
  3. Click top result → place page
  4. Validate: address contains kecamatan AND coords within 2km of expected
  5. Share → Copy Link → clipboard
  6. Store result

Usage: python3 scrape_maps_urls.py [--limit N] [--skip-errors] [--retry-failed]
"""
import asyncio
import json
import math
import re
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


DATA_DIR = Path("/Users/ibnulmutaki/Development/github/sambasku/data")
PLACES_JSON = DATA_DIR / "places.json"
WORKLIST_JSON = DATA_DIR / "places_mapsurl_worklist.json"
RESULTS_JSON = DATA_DIR / "places_mapsurl_results.json"
ADDRESSES_JSON = DATA_DIR / "places_mapsurl_addresses.json"
SKIP_LAT_MISSING = True
# Max distance (km) between scraped coords and expected place coords
MAX_COORD_DIST_KM = 2.0
PAUSE_MS = 2500  # pause between requests (Google rate-limit guard)


# regionId → name map (from regions.json)
def build_region_map() -> dict[str, str]:
    d = json.load(open(DATA_DIR / "regions.json"))
    return {r["id"]: r["name"] for r in d["regions"]}


# RegionId → possible name tokens for matching address text
def build_region_tokens(regions: dict[str, str]) -> dict[str, list[str]]:
    """regionId → list of lowercase strings that should appear in address."""
    tokens: dict[str, list[str]] = {}
    for rid, name in regions.items():
        opts: list[str] = []
        # Kadidat full name + abbreviation variants Google Maps punya
        cand = name.lower()
        opts.append(cand)
        opts.append(cand.replace("-", " "))
        # Google abbreviates: "Teluk Keramat" -> "Tlk. Keramat",
        # "Selakau Timur" -> "Selakau Tim.", "Jawai Selatan" -> "Jawai Sel."
        abbrev_map = {
            "teluk": "tlk",
            "selatan": "sel",
            "timur": "tim",
            "besar": "bes",
            "sungai": "sung",
        }
        for word, abbr in abbrev_map.items():
            if word in cand:
                opts.append(cand.replace(word, abbr))
                # With trailing period: Google writes "Tlk. Keramat"
                opts.append(cand.replace(word, abbr + "."))
        # Parent kecamatan for sub-regions (e.g. "selakau/sungai-rusa" → "selakau")
        parent = rid.split("/")[0]
        if parent != rid and parent in regions:
            opts.append(regions[parent].lower())
        tokens[rid] = list(dict.fromkeys(opts))  # dedupe preserve order
    return tokens


def load_worklist() -> list[dict]:
    with open(WORKLIST_JSON) as f:
        return json.load(f)


def load_results() -> dict[str, str]:
    if RESULTS_JSON.exists():
        with open(RESULTS_JSON) as f:
            return json.load(f)
    return {}


def load_addresses() -> dict[str, str]:
    if ADDRESSES_JSON.exists():
        with open(ADDRESSES_JSON) as f:
            return json.load(f)
    return {}


def save_all(results: dict[str, str], addresses: dict[str, str]):
    with open(RESULTS_JSON, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    with open(ADDRESSES_JSON, "w") as f:
        json.dump(addresses, f, ensure_ascii=False, indent=2)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def extract_coords_from_url(url: str) -> tuple[float, float] | None:
    """Extract @lat,lng from a Google Maps place URL."""
    m = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except ValueError:
            pass
    return None


def validate_result(
    address: str | None,
    page_url: str,
    expected_lat: float | None,
    expected_lng: float | None,
    region_id: str,
    region_tokens_map: dict[str, list[str]],
) -> tuple[bool, str]:
    """Validate scraped result. Returns (valid, reason)."""
    reasons = []

    # Check address vs kecamatan: reject HANYA jika address jelas menyebut
    # kecamatan lain. Alamat tanpa kecamatan (mis. cuma nama desa) biarkan
    # koordinat-check yang memutuskan.
    if address:
        addr_lower = address.lower()
        # "Kabupaten Sambas" / "Sambas Regency" bukan kecamatan Sambas!
        # Strip sebelum matching supaya nama kabupaten tidak tertukar.
        addr_lower = addr_lower.replace(
            "kabupaten sambas", "kabupaten [x]"
        ).replace("sambas regency", "regency [x]")
        tokens = region_tokens_map.get(region_id, [region_id.replace("-", " ")])
        kec_match = any(t in addr_lower for t in tokens)
        if not kec_match:
            for rid, toks in region_tokens_map.items():
                if rid == region_id or rid.split("/")[0] == region_id:
                    continue  # diri sendiri + desa di dalamnya
                if any(t in addr_lower for t in toks):
                    reasons.append(
                        f"kec mismatch: expected {region_id}, got {rid}"
                    )
                    break

    # Check coords from URL
    if expected_lat is not None and expected_lng is not None:
        url_coords = extract_coords_from_url(page_url)
        if url_coords:
            dist = haversine_km(expected_lat, expected_lng, url_coords[0], url_coords[1])
            if dist > MAX_COORD_DIST_KM:
                reasons.append(f"coords {dist:.1f}km > {MAX_COORD_DIST_KM}km limit")

    if reasons:
        return False, "; ".join(reasons)
    return True, "ok"


async def scrape_one(
    page: Page,
    name: str,
    place_id: str,
    kec_name: str,
    lat: float | None,
    lng: float | None,
) -> tuple[str | None, str | None]:
    """Return (maps_url, address) — None if no result."""
    # Navigate fresh to Maps home (avoid stale state from previous iteration)
    await page.goto("https://www.google.com/maps", wait_until="domcontentloaded")
    await page.wait_for_timeout(2500)

    search_q = f"{name} Kec. {kec_name} Kabupaten Sambas"
    search_box = page.locator("input[name='q']").first

    try:
        await search_box.wait_for(state="visible", timeout=10000)
        await search_box.click()
        await search_box.fill(search_q)
        await page.wait_for_timeout(500)
        await search_box.press("Enter")
        await page.wait_for_timeout(3000)
    except Exception as e:
        print(f"  [WARN] search failed: {e}", end="")
        return None, None

    url = page.url

    # If we landed on a place page directly
    if "/place/" in url:
        pass  # proceed to address/share flow below
    elif "maps/search" in url or "search" in url:
        # Click first result
        try:
            first_result = page.locator("div[role='article']").first
            await first_result.click(timeout=5000)
            await page.wait_for_timeout(2500)
        except Exception:
            try:
                first_item = page.locator("[data-result-index='0']").first
                await first_item.click(timeout=3000)
                await page.wait_for_timeout(2500)
            except Exception:
                pass

    # Capture address
    address = None
    try:
        addr_el = page.locator("button[data-item-id='address']")
        address = await addr_el.inner_text(timeout=3000)
    except Exception:
        try:
            address = await page.locator("h1").first.inner_text(timeout=2000)
        except Exception:
            pass

    final_url = page.url

    # Click Share → Copy Link (tombol di region "Tindakan untuk ...", bukan di feed)
    try:
        # Feed juga punya tombol Bagikan; scope ke region dengan data-value
        # (tombol action pane tempat detail).
        share_btn = page.locator(
            "div[role='region'] button[data-value='Bagikan'], button[data-value='Bagikan']"
        ).first
        await share_btn.wait_for(state="visible", timeout=8000)
        await share_btn.click(timeout=5000)
        await page.wait_for_timeout(800)

        copy_btn = page.get_by_role("button", name="Copy Link")
        await copy_btn.click(timeout=5000)
        await page.wait_for_timeout(600)

        clip = await page.evaluate("navigator.clipboard.readText()")
        if clip and ("maps.app.goo.gl" in clip or "goo.gl/maps" in clip):
            try:
                await page.keyboard.press("Escape")
                await page.wait_for_selector("[role='dialog']", state="hidden", timeout=3000)
            except Exception:
                pass
            return clip, address
    except Exception as e:
        print(f"  [WARN] share flow failed: {e}", end="")

    # Ensure dialog closed
    try:
        await page.keyboard.press("Escape")
        await page.wait_for_selector("[role='dialog']", state="hidden", timeout=2000)
    except Exception:
        pass

    return None, address


async def main(limit: int | None = None, skip_errors: bool = False, retry_failed: bool = False):
    regions = build_region_map()
    region_tokens = build_region_tokens(regions)
    places = load_worklist()

    if retry_failed:
        results = load_results()
        failed_ids = {k for k, v in results.items() if not v.startswith("https://")}
        # Remove failed entries so they get re-scraped
        for fid in failed_ids:
            del results[fid]
        save_all(results, load_addresses())
        print(f"Removed {len(failed_ids)} failed entries for retry")

    if limit:
        places = places[:limit]

    results = load_results()
    addresses = load_addresses()
    done = set(results.keys())
    todo = [p for p in places if p["id"] not in done]

    print(f"Total: {len(places)} | Done: {len(done)} | To do: {len(todo)}")

    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        ctx: BrowserContext = await browser.new_context(
            permissions=["clipboard-read", "clipboard-write"],
            viewport={"width": 1280, "height": 900},
        )
        page: Page = await ctx.new_page()

        for i, place in enumerate(todo):
            pid = place["id"]
            name = place["name"]
            lat = place.get("lat")
            lng = place.get("lng")
            region = place.get("regionId", "")
            kec_name = regions.get(region, region.replace("-", " "))

            print(f"[{i+1}/{len(todo)}] {pid} ({region}={kec_name}) ...", end=" ", flush=True)

            if SKIP_LAT_MISSING and (lat is None or lng is None):
                print("SKIP (no coords)")
                continue

            try:
                url, address = await scrape_one(page, name, pid, kec_name, lat, lng)

                if address:
                    addresses[pid] = address

                if url:
                    valid, reason = validate_result(
                        address, url, lat, lng, region, region_tokens
                    )
                    if valid:
                        results[pid] = url
                        save_all(results, addresses)
                        short = url[:65] + ("..." if len(url) > 65 else "")
                        addr_log = f" | addr: {address[:55]}" if address else ""
                        print(f"OK ✓ {short}{addr_log}")
                    else:
                        # Wrong place — don't save, log reason
                        addr_log = f" | addr: {address[:55]}" if address else ""
                        print(f"REJECT ✗ [{reason}]{addr_log}")
                        if not skip_errors:
                            results[pid] = "REJECTED"
                            save_all(results, addresses)
                else:
                    addr_log = f" | addr: {address[:55]}" if address else ""
                    print(f"NO RESULT{addr_log}")
                    if not skip_errors:
                        results[pid] = "FAILED"
                        save_all(results, addresses)
            except Exception as e:
                print(f"ERROR: {e}")
                if not skip_errors:
                    results[pid] = f"ERROR:{e}"
                    save_all(results, addresses)

            await page.wait_for_timeout(PAUSE_MS)

        await browser.close()

    ok = sum(1 for v in results.values() if v.startswith("https://"))
    rejected = sum(1 for v in results.values() if v == "REJECTED")
    print(f"\nDone. OK: {ok} | Rejected: {rejected} | Results in {RESULTS_JSON}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit to N places")
    parser.add_argument("--skip-errors", action="store_true", help="Continue on errors")
    parser.add_argument("--retry-failed", action="store_true", help="Re-scrape previously failed/rejected entries")
    args = parser.parse_args()

    asyncio.run(main(limit=args.limit, skip_errors=args.skip_errors, retry_failed=args.retry_failed))