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

Objek wisata: 2 entri kurasional + 180 entri dari [Open Data Sambas](https://opendata.sambas.go.id) (dataset 116, opendata.sambas.go.id/json/116, 2023, `uraian`/`keterangan`/`jumlah`).

| Sumber | Lisensi |
| ------ | ------- |
| [Open Data Sambas - dataset 116](https://opendata.sambas.go.id/json/116) | CC BY-SA 4.0 |

Atribusi tiap entri tertanam di `sources` (`name: Open Data Sambas - Objek Wisata (dataset 116)`). Entri Open Data belum punya koordinat (`lat`/`lng` null) dan pakai gambar placeholder Elementor (`images[].url`), menunggu foto asli di repo `images`. `regionId` = kecamatan pertama bila sumber mencantumkan lebih dari satu kecamatan.

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
