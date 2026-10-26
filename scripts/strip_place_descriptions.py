#!/usr/bin/env python3
"""Buang deskripsi per place dari artikel kecamatan.

Generator `refresh_district_md.py` kini hanya menulis nama, jadi file yang
sudah di-commit harus disejajarkan: bullet `- **Nama** - deskripsi` -> `- **Nama**`.
"""
import re
import sys
from pathlib import Path

MD_DIR = Path(__file__).resolve().parent.parent / 'markdown' / 'district'
BULLET = re.compile(r'^- \*\*(.+?)\*\* - .+$')


def main() -> int:
    changed = 0
    for path in sorted(MD_DIR.glob('*.md')):
        lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
        out = []
        hits = 0
        for line in lines:
            m = BULLET.match(line.rstrip('\n'))
            if m:
                out.append(f'- **{m.group(1)}**\n')
                hits += 1
            else:
                out.append(line)
        if hits:
            path.write_text(''.join(out), encoding='utf-8')
            changed += 1
            print(f'{path.name}: {hits} bullet dirapikan')
    print(f'Selesai: {changed} file diubah')
    return 0


if __name__ == '__main__':
    sys.exit(main())
