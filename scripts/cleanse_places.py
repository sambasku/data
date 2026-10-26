#!/usr/bin/env python3
"""
Cleanse places.json: keep only factual fields.
Keep: id, slug, name, category, lat, lng, regionId, mapsUrl, status.
"""

import json
import sys
from pathlib import Path

PLACES = Path(__file__).resolve().parent.parent / 'places.json'

def cleanse_places():
    with open(PLACES, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    places = data['places']
    original_count = len(places)
    
    # Track coordinates to verify no change
    original_coords = {p['id']: (p['lat'], p['lng']) for p in places}
    
    # Cleanse each place: keep only 9 fields
    cleansed = []
    for place in places:
        cleaned = {
            'id': place['id'],
            'slug': place['slug'],
            'name': place['name'],
            'category': place['category'],
            'lat': place['lat'],
            'lng': place['lng'],
            'regionId': place['regionId'],
            'mapsUrl': place.get('mapsUrl'),  # May be null for 13 places
            'status': place.get('status', 'published'),
        }
        cleansed.append(cleaned)
    
    # Verify count
    if len(cleansed) != original_count:
        print(f"ERROR: Place count changed. Before: {original_count}, After: {len(cleansed)}")
        sys.exit(1)
    
    # Verify coordinates unchanged
    for place in cleansed:
        orig_lat, orig_lng = original_coords[place['id']]
        if place['lat'] != orig_lat or place['lng'] != orig_lng:
            print(f"ERROR: Coordinates changed for {place['id']}")
            sys.exit(1)
    
    # Write back
    output = {
        'version': 1,
        'license': 'CC BY-SA 4.0',
        'places': cleansed
    }
    
    with open(PLACES, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Cleansed {len(cleansed)} places")
    print(f"✓ Coordinates verified unchanged")
    print(f"✓ File saved")

if __name__ == '__main__':
    cleanse_places()
