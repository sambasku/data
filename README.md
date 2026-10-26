# data

Sumber data statis publik (dilayani via jsDelivr: `cdn.jsdelivr.net/gh/sambasku/data@main/...`).

## regions.json / regions.geojson

Wilayah Kabupaten Sambas: 19 kecamatan, 195 desa/kelurahan.

| Sumber | Lisensi |
| ------ | ------- |
| [geoBoundaries gbHumanitarian IDN ADM3](https://www.geoboundaries.org/countryDownloads.html?id=IDN-ADM3) (polygon kecamatan) | CC BY 3.0 IGO |
| [Wikidata daftar desa Kab. Sambas](https://www.wikidata.org/wiki/Q14164) (daftar desa) | CC0 |

Lisensi gabungan: CC BY-SA 4.0. Metadata juga tertanam di field `sources` regions.json.

Catatan: `id` memakai slug internal (`kecamatan/desa`), bukan kode Kemendagri. Semua entri
level desa berlabel `desa` (tidak dibedakan dari kelurahan).

## places.json

**Non-SoT setelah Places CRUD.** Sumber kebenaran live = tabel Turso
`places` / `place_images` via API (`docs/backlogs/PLACES_CRUD.md`).
File ini tetap dipakai sebagai **seed/backup** (`pnpm seed:places` di
`api/`). Jangan andalkan CDN ini sebagai alur edit harian.

114 entri, field per place dibatasi ke data faktual saja:

| Field | Catatan |
| ----- | ------- |
| `id`, `slug`, `name` | identitas place |
| `category` | `wisata` / `kuliner` / `budaya` |
| `lat`, `lng` | koordinat (boleh null) |
| `regionId` | slug kecamatan; desa (`village_id`) diisi admin lewat console |
| `mapsUrl` | tautan Google Maps (boleh null) |
| `status` | selalu `published` di seed |

Deskripsi, foto, jam buka, kontak, alamat, dan `sources` per place **tidak lagi
disimpan di file ini** - semuanya diisi lewat console (SoT Turso).

Kredit dataset tingkat repo (daftar nama objek wisata awal):

| Sumber | Lisensi |
| ------ | ------- |
| [Open Data Sambas - dataset 116](https://opendata.sambas.go.id/json/116) | CC BY-SA 4.0 |

## regions-ref-kemendagri.json

Subset kode wilayah Kemendagri untuk Kab. Sambas, untuk dikompare/di-join dengan
regions.json.

| Sumber | Lisensi |
| ------ | ------- |
| [open-admin-data/indonesia-administrative-divisions](https://github.com/open-admin-data/indonesia-administrative-divisions) | CC-BY-4.0 |

Snapshot Kepmendagri 184 desa, sedangkan regions.json 195 (beda tahun snapshot; ada
desa yang di-split/gabung). Berisi kode + nama kecamatan dan desa.

## scripts/regions_connector.py

Konektor read-only antara regions.json dan regions-ref-kemendagri.json. Stdlib saja.

```bash
python3 scripts/regions_connector.py           # laporan kompare (match/unmatch)
python3 scripts/regions_connector.py --enrich  # tulis data/regions-with-codes.draft.json
```

Output `data/regions-with-codes.draft.json` = schema regions.json + field `code` (Kemendagri)
untuk region yang match. Draft, jangan dipakai produksi sebelum 12 desa unmatched
ditinjau.


## Rules CDN (jsDelivr)

1. **Setiap push ke `main` otomatis purge seluruh file** via GitHub Action
   `.github/workflows/purge-jsdelivr.yml` (purge penuh, chunk 50 path/request).
   Tidak perlu purge manual lagi.
2. **Menambah file data baru**: cukup `git add` + commit + push ke `main` -
   workflow purge otomatis meng-cover file baru (purge penuh, bukan diff).
   File baru bisa langsung diakes via `https://cdn.jsdelivr.net/gh/sambasku/data@main/<path>`
   setelah workflow selesai (~1 menit).
3. **Setelah push, cek Action hijau** (tab Actions repo data) bila file baru
   dibutuhkan segera; purge pending maksimal beberapa menit.
4. Jangan hapus workflow ini; cache jsDelivr ~12 jam tanpa purge.
