#!/usr/bin/env python3
# ponytail: single-purpose generator; upgrade path = parameterize sections per-kecamatan.
"""Regenerasi artikel kecamatan data/markdown/district/<slug>.md.

Sumber: Wikipedia id (naratif, CC BY-SA 4.0) + BPS Dalam Angka 2025 (statistik)
+ OpenData Sambas json/116 (objek wisata) + places.json (wisata fallback).
CLI: --slug <slug> | --all | --dry-run | --resume
"""
import json, os, re, sys, time, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
MD_DIR = os.path.join(ROOT, 'markdown', 'district')
UA = {'User-Agent': 'sambasku-data/1.0 (repo: sambasku/data)'}

BPS = json.load(open(os.path.join(BASE, 'bps_311.json')))

# jumlah desa resmi (desa_2025.csv; baris "Sambas,195" = sampah, fix ke 18)
DESA = {'Selakau':11,'Selakau Timur':4,'Pemangkat':8,'Semparuk':5,'Salatiga':5,
        'Tebas':23,'Tekarang':7,'Sambas':18,'Subah':13,'Sebawi':7,'Sajad':4,
        'Jawai':13,'Jawai Selatan':9,'Teluk Keramat':25,'Galing':10,'Tangaran':8,
        'Sejangkung':12,'Sajingan Besar':5,'Paloh':8}

SKIP_SECTIONS = {'rujukan','pranala luar','lihat pula','catatan','galeri','referensi'}

def api(params, retries=3):
    url = 'https://id.wikipedia.org/w/api.php?' + urllib.parse.urlencode(params)
    for a in range(retries):
        try:
            time.sleep(1.3)
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
        except Exception as e:
            if '429' in str(e):
                time.sleep(15*(a+1)); continue
            raise
    return {}

def fmt_id(n):
    s = f'{n:,.0f}'
    return s.replace(',', '.')

def resolve_title(nama):
    for t in (f'{nama}, Sambas', f'Kecamatan {nama}', nama):
        d = api({'action':'query','prop':'info','titles':t,'format':'json'})
        pages = d.get('query',{}).get('pages',{})
        for pid, p in pages.items():
            if int(pid) > 0 and 'missing' not in p:
                return p['title']
    d = api({'action':'query','list':'search','srsearch':f'{nama} kecamatan Sambas','format':'json'})
    hits = d.get('query',{}).get('search',[])
    return hits[0]['title'] if hits else None

def get_wikitext(title):
    d = api({'action':'query','prop':'revisions','rvprop':'content','rvslots':'main',
             'titles':title,'format':'json','redirects':1})
    for p in d.get('query',{}).get('pages',{}).values():
        for rv in p.get('revisions',[]):
            return rv['slots']['main']['*']
    return ''

def hero_image(wikitext, title):
    # cari [[Berkas:/File: pertama di infobox foto= lalu di body
    m = re.search(r'\|\s*(?:foto|image|image_map)\s*=\s*([^|\n}]+)', wikitext)
    if not m:
        m = re.search(r'\[\[(?:Berkas|File):([^\]|]+)', wikitext)
    if not m:
        return None
    fn = m.group(1).strip()
    if not re.search(r'\.(jpe?g|png|webp|gif)$', fn, re.I):
        return None
    d = api({'action':'query','prop':'imageinfo','iiprop':'url|extmetadata',
             'iiurlwidth':'1200','titles':f'File:{fn}','format':'json'})
    for p in d.get('query',{}).get('pages',{}).values():
        ii = p.get('imageinfo')
        if ii and 'missing' not in p:
            meta = ii[0].get('extmetadata',{})
            artist = re.sub(r'<[^>]+>','',meta.get('Artist',{}).get('value','') or '').strip() or 'Wikimedia Commons'
            lic = meta.get('LicenseShortName',{}).get('value','') or ''
            return {'url': ii[0].get('thumburl') or ii[0]['url'], 'artist': artist, 'license': lic}
    return None

def _tbl2md(text):
    """Convert {|...|} wikitable ke markdown table, atau hapus jika parse gagal."""
    # match entire table
    def conv(m):
        raw = m.group(0)
        lines = raw.split('\n')
        rows = []
        for ln in lines[1:]:
            ln = ln.strip()
            if not ln or ln.startswith('|-') or ln.startswith('|}'): continue
            if ln.startswith('|!' or ln.startswith('!')):
                sep = '!' if ln.startswith('!') else '|'
                cells = [c.strip() for c in ln[1 if ln[1] in '|!' else 0:].split(sep) if c.strip()]
                rows.append(cells)
            elif ln.startswith('|'):
                cells = [c.strip() for c in re.split(r'\|\|?', ln[1:]) if c.strip()]
                rows.append(cells)
        if len(rows) < 2 or not rows[0]: return ''
        header, *data = rows
        # drop first col if it's a row-number column (all cells == row index)
        if len(header) > 1 and all(re.match(r'^\d+$', str(c)) for c in header):
            header = header[1:]; data = [r[1:] for r in data]
        out = []
        out.append('| ' + ' | '.join(str(h) for h in header) + ' |')
        out.append('| ' + ' | '.join('---' for _ in header) + ' |')
        for row in data:
            cells = row + [''] * (len(header) - len(row))
            out.append('| ' + ' | '.join(str(c) for c in cells[:len(header)]) + ' |')
        return '\n'.join(out)
    # replace all tables
    return re.sub(r'\{\|[\s\S]*?\|\}', conv, text)

def strip_wiki(text):
    # stash markdown links (shouldn't exist yet) & protect
    text = re.sub(r'<ref[^>]*/>', '', text)
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.S)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    # convert wikitable before any template processing (tables use {|...|}, no braces inside)
    text = _tbl2md(text)
    # templates: ulang sampai habis (nested) — skip {|...|} already handled
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r'\{\{[^{}|\n][^{}]*\}\}', '', text)  # skip {| inside
    # bold/italic
    text = text.replace("'''", '').replace("''", '')
    # wiki links: [[target|label]] -> label; [[target]] -> target
    # also handle broken: [[target|label (no close) -> target
    def wl(m):
        inner = m.group(1)
        # split by |; last part is label if it exists
        parts = inner.split('|')
        if len(parts) == 1:
            target = parts[0].strip()
            # external link inside [[..| [url label] ]]
            em = re.match(r'\[(\S+)\s+([^\]]+)\]', target)
            if em:
                return f'[{em.group(2)}]({em.group(1)})'
            # pure namespace link -> plain text
            if ':' in target and not target.startswith('http'):
                ns = target.split(':')[0]
                if ns in ('Berkas','File','Kategori','Category','Image','w','en'):
                    return ''
            return target
        # has | — label is last part
        label = parts[-1].strip()
        # if label is empty (broken [[x| ) use target
        if not label:
            label = parts[0].strip()
        if label.startswith('Berkas:') or label.startswith('File:'):
            return ''
        em = re.match(r'\[(\S+)\s+([^\]]+)\]', label)
        if em:
            return f'[{em.group(2)}]({em.group(1)})'
        if ':' in label and not label.startswith('http'):
            ns = label.split(':')[0]
            if ns in ('Berkas','File','Kategori','Category','Image','w','en'):
                return ''
        return label
    text = re.sub(r'\[\[([^\[\]]+)\]\]', wl, text)
    # also catch unclosed [[target| (no closing brackets) — convert to target
    text = re.sub(r'\[\[([^\[\]|]+)\|[^\]]*$', lambda m: m.group(1).strip(), text, flags=re.M)
    # also catch unclosed [[target (no closing at all)
    text = re.sub(r'\[\[([^\[\]|]+)[^\]]*$', lambda m: m.group(1).strip(), text, flags=re.M)
    # external links [url label] -> [label](url)
    text = re.sub(r'\[(https?://\S+)[ \t]+([^\]]+)\]', r'[\2](\1)', text)
    text = re.sub(r'\[(https?://\S+)\]', r'<\1>', text)
    # heading: ==x== -> ##, ===x=== -> ### (standalone lines only)
    lines = text.split('\n')
    out = []
    for ln in lines:
        stripped = ln.strip()
        m = re.match(r'^(={2,6})\s*(.+?)\s*\1$', stripped)
        if m:
            lvl = min(len(m.group(1)), 4) + 1  # == -> h2, === -> h3
            out.append('#' * lvl + ' ' + m.group(2))
        else:
            out.append(ln)
    text = '\n'.join(out)
    # ordered list: consecutive wiki '# item' lines -> numbered
    # '# Item' maupun '#Item' tanpa spasi sama-sama list wiki
    def _renum(m):
        items = [l for l in m.group(0).split('\n') if l.strip()]
        out = []
        for i, l in enumerate(items):
            item = re.sub(r"^#+\s*", "", l).strip()
            out.append(f'{i+1}. {item}')
        return '\n'.join(out)
    text = re.sub(r'(?:^#[ \t]*[^\s#].*\n?)+', _renum, text, flags=re.M)
    # HTML cleanup
    text = text.replace('&nbsp;', ' ')
    text = re.sub(r'<sup>\s*2\s*</sup>', '²', text)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</?(?:small|nowiki|gallery|center|big|u|s|sub|blockquote|div|span)[^>]*>', '', text)
    # list: lines starting with ; or * or :
    text = re.sub(r'^;+[ \t]*', '- ', text, flags=re.M)
    text = re.sub(r'^[\*\:]+[ \t]*', '- ', text, flags=re.M)
    # residual brackets cleanup via stash-restore
    return text

def sanitize(md):
    # 1) stash valid links
    stashed = []
    def stash(m):
        stashed.append(m.group(0)); return f'\x00{len(stashed)-1}\x00'
    md = re.sub(r'!?\[[^\]]*\]\([^)]+\)', stash, md)
    # 2) buang bracket liar
    md = md.replace('[[','').replace(']]','')
    md = re.sub(r'\(\s*\)', '', md)  # hanya kurung kosong betulan
    md = re.sub(r'(?<!\x00\d)\[([^()\[\]]*)\]', r'\1', md)  # [x] tanpa ( -> x
    # 3) restore
    md = re.sub(r'\x00(\d+)\x00', lambda m: stashed[int(m.group(1))], md)
    # buang heading tanpa konten sampai heading berikutnya
    md = re.sub(r'\n(#{2,6} [^\n]+)\n+(?=#)', r'\n\1\n\n', md)
    # blank line sebelum heading
    md = re.sub(r'([^\n])\n(#{1,6} )', r'\1\n\n\2', md)
    # collapse >2 blank
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md.strip()

def opendata_wisata(slug_nama):
    try:
        d = json.load(open(os.path.join(BASE,'opendata','116.json')))
    except Exception:
        return []
    nama = slug_nama.lower()
    pat = re.compile(r'kec(?:amatan)?\.?\s*' + re.escape(nama), re.I)
    out, seen = [], set()
    for r in d.get('data',[]):
        if not pat.search(r.get('jumlah','') or ''):
            continue
        nm = (r.get('keterangan') or '').strip()
        key = re.sub(r"['’\s]+", '', nm.lower())
        if nm and key not in seen:
            seen.add(key); out.append(nm)
    return out[:8]

def build(slug, dry=False):
    bps = BPS[slug]
    nama = bps['nama']
    title = resolve_title(nama)
    if not title:
        return f'{slug}: SKIP (no wikipedia article)'
    wikitext = get_wikitext(title)
    hero = hero_image(wikitext, title)

    b = bps
    ringkasan = [
        f'**Nama resmi**: Kecamatan {nama}',
        f'**Ibu kota**: {_seat(nama)}',
        f'**Jumlah desa**: {DESA[nama]}',
        f'**Luas wilayah**: {fmt_id(b["luas"])} km²',
        f'**Penduduk**: {fmt_id(b["penduduk"])} jiwa (2024)',
        f'**Kepadatan**: {fmt_id(b["kepadatan"])} jiwa/km²',
        f'**Laju pertumbuhan**: {b["laju"]:.2f}% per tahun (2020-2024)',
        f'**Rasio jenis kelamin**: {b["rasio"]:.2f} (L/P)',
    ]
    wisata = opendata_wisata(nama)

    parts = [f'# Kecamatan {nama}', '']
    if hero:
        parts.append(f'![{nama}]({hero["url"]})')
        parts.append('')
    # lead: paragraf pertama bersih
    body = strip_wiki(wikitext)
    # buang sisa infobox-style "nama = " lines di awal
    body = re.sub(r'^[A-Za-z _\-]+\s*=\s*[^\n]*\n', '', body, flags=re.M)
    paras = [p.strip() for p in body.split('\n\n') if p.strip()]
    lead = paras[0] if paras else f'Kecamatan {nama} adalah salah satu dari 19 kecamatan di Kabupaten Sambas, Kalimantan Barat.'
    # lead jangan heading
    lead = re.sub(r'^#{1,6}\s*', '', lead)
    parts += [lead, '', '## Ringkasan', '']
    parts += [f'- {l}' for l in ringkasan]
    parts.append('')
    parts.append('Sumber statistik: BPS, *Kabupaten Sambas Dalam Angka 2025* (Tabel 3.1.1).')
    parts.append('')
    # sections dari body (skip lead)
    for p in paras[1:]:
        h = re.match(r'^#{1,6}\s+(.+)$', p.split('\n')[0])
        if h and h.group(1).strip().lower() in SKIP_SECTIONS:
            continue
        parts.append(p if p.startswith('#') or p.startswith('-') else p)
        parts.append('')
    if wisata:
        parts.append('## Wisata')
        parts.append('')
        parts.append(f'Objek wisata terdaftar di Open Data Kabupaten Sambas (2024):')
        parts.append('')
        parts += [f'- {w}' for w in wisata]
        parts.append('')
    parts.append('---')
    parts.append('')
    parts.append(f'Sumber: [Wikipedia bahasa Indonesia - {title}](https://id.wikipedia.org/wiki/{urllib.parse.quote(title.replace(" ","_"))}) (CC BY-SA 4.0) · Statistik: BPS *Kabupaten Sambas Dalam Angka 2025* · Wisata: Open Data Kabupaten Sambas 2024.')
    if hero:
        lic = f' ({hero["license"]})' if hero['license'] else ''
        parts.append(f'Foto: {hero["artist"]}{lic}')
    md = sanitize('\n'.join(parts)) + '\n'
    if dry:
        return f'{slug}: {len(md)}B, hero={"ya" if hero else "tidak"}, wisata={len(wisata)}'
    path = os.path.join(MD_DIR, f'{slug}.md')
    if os.path.exists(path) and os.path.getsize(path) > 1500:
        with open(path) as f: old = f.read()
    else:
        old = None
    with open(path, 'w') as f:
        f.write(md)
    return f'{slug}: OK ({len(md)}B{" (existing " + str(len(old)) + "B)" if old else ""})'

def _seat(nama):
    seats = {'Selakau':'Selakau','Selakau Timur':'Selakau Tua','Pemangkat':'Pemangkat',
             'Semparuk':'Semparuk','Salatiga':'Salatiga','Tebas':'Tebas','Tekarang':'Tekarang',
             'Sambas':'Sambas','Subah':'Balai Gemuruh','Sebawi':'Sebawi','Sajad':'Tengguli',
             'Jawai':'Sentebang','Jawai Selatan':'Matang Terap','Teluk Keramat':'Sekura',
             'Galing':'Galing','Tangaran':'Simpang Empat','Sejangkung':'Sejangkung',
             'Sajingan Besar':"Kaliau'",'Paloh':'Liku'}
    return seats.get(nama, nama)

def main():
    args = sys.argv[1:]
    dry = '--dry-run' in args
    resume = '--resume' in args
    slugs = BPS.keys() if '--all' in args else [a for a in args if not a.startswith('--')]
    if '--slug' in args:
        slugs = [args[args.index('--slug')+1]]
    for slug in slugs:
        if resume:
            p = os.path.join(MD_DIR, f'{slug}.md')
            if os.path.exists(p) and os.path.getsize(p) > 1500:
                print(f'{slug}: resume-skip'); continue
        print(build(slug, dry=dry), flush=True)

if __name__ == '__main__':
    main()
