# Data Wilayah Sambas: Kecamatan dan Desa

## File

- `regions.json` - daftar 19 kecamatan + 195 desa, dengan centroid kecamatan dan kode BPS 10-digit desa.
- `regions.geojson` - polygon 19 kecamatan (tersederhanakan, ~21 KB, 500
  titik), siap dipakai MapLibre/Leaflet.

## Skema `regions.json`
```json
{
  "version": 2,
  "license": "CC BY-SA 4.0",
  "sources": [...],
  "regions": [
    { "id": "sambas", "name": "Sambas", "type": "kecamatan", "lat": 1.346, "lng": 109.310 },
    { "id": "sambas/semeto", "name": "Semeto", "type": "desa", "parentId": "sambas", "code": "6101040029" }
  ]
}
```

- `id` kecamatan: slug nama. `id` desa: `<slug-kecamatan>/<slug-desa>`.
- `parentId` desa = slug kecamatan induknya.
- `lat`/`lng` hanya ada di kecamatan (centroid, untuk kamera/pin).
- `code` (opsional) = kode BPS 10-digit, hanya di desa (format: 61=prov Kalbar, 01=kab Sambas, 3 digit kec, 4 digit desa).

## Skema `regions.geojson`

FeatureCollection; per feature: `properties: {id, name, type: "kecamatan"}` +
geometry Polygon/MultiPolygon (koordinat [lng, lat]).

## Sumber dan Lisensi

| Sumber | Isi | Lisensi |
|--------|-----|---------|
| geoBoundaries gbHumanitarian IDN ADM3 (2019, via OCHA ROAP/HDX) | polygon kecamatan | CC BY 3.0 IGO |
| DPMD Kabupaten Sambas - Daftar Kode dan Nama Desa (artikel 36) | nama desa resmi + kode BPS 10-digit | Pemerintah Daerah |
| BPS Kabupaten Sambas - Jumlah Desa/Kelurahan Menurut Kecamatan, 2025 | verifikasi jumlah (195 desa) | BPS |

Polygon sudah disederhanakan (Douglas-Peucker, epsilon 0.004 derajat) saat
pembuatan; regenerasi manual, tidak ada pipeline otomatis.

## Konsumsi

- Mobile: `regions.json` via CDN jsdelivr (`data@main`), `regions.geojson`
  di-bundle sebagai asset (`mobile/assets/data/regions.geojson`).
- Pencocokan nama polygon <-> kode Kemendagri dilakukan by nama ternormalisasi
  saat pembuatan; hasilnya sudah ter-commit di kedua file.

## Validasi Data

Aturan: **Tidak pernah hitung manual**. Jumlah kecamatan (19) dan desa (195)
**harus divalidasi programmatis** dari sumber DPMD/BPS sebelum commit.
Lihat `.cursor/rules/data-validation.mdc`.
## ADM4 (Desa) Polygon Data

- `regions-adm4.geojson` - 193 desa polygons dari HDX/geoBoundaries gbHumanitarian ADM4 (CC BY 3.0 IGO), disederhanakan ke ~67 KB (epsilon 0.003°, 4 desimal), siap bundle mobile.
- 2 desa dari DPMD tidak ada di HDX: Arga Pura (6101102012), Sapak Hulu Trans (6101102013) - keduanya di Kecamatan Subah.
- Properti: `id` (slug kecamatan/desa), `name`, `type: "desa"`, `parentId` (slug kecamatan), `code` (BPS 10-digit).
- Cocokkan dengan `regions.json` via field `code` (BPS 10-digit).
- Mobile asset: `mobile/assets/data/regions-adm4.geojson` (67 KB).
