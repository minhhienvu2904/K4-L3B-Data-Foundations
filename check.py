import csv, re
from pathlib import Path

D = Path('data/chinh-sach-doi-tra-tiki')
REQ = ['doc_id', 'title', 'source_url', 'retrieved_at', 'document_version', 'audience']

mds = sorted(D.glob('*.md'))
rows = list(csv.DictReader(open(D / 'sources.csv', encoding='utf-8')))
ids, auds = [], {}

for p in mds:
    fm = dict(re.findall(r'^(\w+):\s*(.+)$', p.read_text(encoding='utf-8').split('---')[1], re.M))
    ids.append(fm.get('doc_id'))
    auds[fm.get('audience')] = auds.get(fm.get('audience'), 0) + 1
    ok = all(k in fm for k in REQ) and fm.get('doc_id') == p.stem
    print(f'{p.name:40} {"OK" if ok else "THIEU METADATA"}')

print('so file :', len(mds), '(can 5-10)')
print('csv     :', 'khop' if sorted(r['doc_id'] for r in rows) == sorted(ids) else 'LECH')
print('audience:', auds)