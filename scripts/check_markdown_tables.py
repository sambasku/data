#!/usr/bin/env python3
"""Cek tabel GFM di markdown/**: header, delimiter, dan tiap baris wajib jumlah kolom sama.
Exit 1 kalau ada yang rusak (tabel rusak tampil sebagai teks pipe mentah di mobile, #161)."""
import glob, os, re, sys

BASE = os.path.join(os.path.dirname(__file__), '..', 'markdown')
DELIM = re.compile(r'^\s*\|?\s*(:?-+:?\s*\|\s*)*:?-+:?\s*\|?\s*$')

def cols(line):
    s = line.strip().removeprefix('|').removesuffix('|')
    return len(s.split('|'))

bad = 0
for path in sorted(glob.glob(os.path.join(BASE, '**', '*.md'), recursive=True)):
    lines = open(path, encoding='utf-8').read().splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith('|') and i + 1 < len(lines) and lines[i + 1].startswith('|') and DELIM.match(lines[i + 1]):
            n, j = cols(lines[i]), i
            while j < len(lines) and lines[j].startswith('|'):
                if cols(lines[j]) != n:
                    print(f'{os.path.relpath(path, BASE)}:{j + 1}: {cols(lines[j])} kolom, header {n}')
                    bad += 1
                j += 1
            i = j
        else:
            i += 1
sys.exit(1 if bad else 0)
