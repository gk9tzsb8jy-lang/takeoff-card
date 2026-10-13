"""Merge FAA NASR declared distances (TORA/ASDA) into runways.json.

Run by .github/workflows/faa-declared-distances.yml. Optional argument: a local
APT_CSV zip to use instead of downloading (for testing).
"""
import csv, datetime as dt, io, json, re, sys, urllib.request, zipfile

UA = {'User-Agent': 'takeoff-card (github.com/gk9tzsb8jy-lang/takeoff-card)'}
EPOCH = dt.date(2025, 1, 23)  # a known AIRAC / NASR effective date


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def cycles():
    """Current NASR cycle date first, then the one before it."""
    n = (dt.date.today() - EPOCH).days // 28
    return [EPOCH + dt.timedelta(days=28 * k) for k in (n, n - 1)]


def download():
    for d in cycles():
        url = f"https://nfdc.faa.gov/webContent/28DaySub/extra/{d:%d_%b_%Y}_APT_CSV.zip"
        try:
            print('trying', url); return d, get(url)
        except Exception as e:
            print('  no:', e)
    # Fallback: find the link on the FAA subscription pages.
    base = 'https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/'
    for d in cycles():
        try:
            page = get(f'{base}{d:%Y-%m-%d}').decode('utf-8', 'replace')
        except Exception as e:
            print('  page', d, e); continue
        m = re.search(r'https?://[^"\']+APT_CSV\.zip', page)
        if m:
            print('found', m.group(0)); return d, get(m.group(0))
    sys.exit('Could not find the FAA APT_CSV zip for the current or previous cycle.')


def col(header, *need):
    for h in header:
        if all(n in h for n in need):
            return h
    sys.exit(f'Column with {need} not found. Header: {header}')


def num(s):
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return 0


def end_key(s):
    return (s or '').strip().upper().lstrip('0')


def main():
    if len(sys.argv) > 1:
        cyc, blob = dt.date.today(), open(sys.argv[1], 'rb').read()
    else:
        cyc, blob = download()
    z = zipfile.ZipFile(io.BytesIO(blob))
    name = next(n for n in z.namelist() if n.upper().endswith('APT_RWY_END.CSV'))
    rows = list(csv.DictReader(io.TextIOWrapper(z.open(name), 'latin-1')))
    h = list(rows[0].keys())
    print('columns:', h)
    c_apt, c_end = col(h, 'ARPT_ID'), col(h, 'RWY_END_ID')
    c_tora, c_asda = col(h, 'TKOF_RUN'), col(h, 'ACLT_STOP')
    c_eff = next((x for x in h if x == 'EFF_DATE'), None)
    if c_eff and rows[0].get(c_eff):
        print('FAA effective date:', rows[0][c_eff])

    dd = {}
    for r in rows:
        t, a = num(r[c_tora]), num(r[c_asda])
        if t or a:
            dd[(r[c_apt].strip().upper(), end_key(r[c_end]))] = (t, a)
    print(len(dd), 'runway ends with declared distances')

    db = json.load(open('runways.json'))
    A, X = db['a'], db['x']
    # Map each database airport to its FAA identifier.
    faa = {}
    for k in A:
        if len(k) == 4 and k[0] == 'K':
            faa.setdefault(k[1:], k)
    for alias, k in X.items():
        faa.setdefault(alias, k)
    for k in A:
        faa.setdefault(k, k)
    by_apt = {}
    for fid, k in faa.items():
        by_apt.setdefault(k, set()).add(fid)

    hits = 0
    for k, (name_, elev, rws) in A.items():
        ids = by_apt.get(k, ())
        for r in rws:
            r[:] = r[:8]
            vals = []
            for e in (r[0], r[1]):
                v = next((dd[(i, end_key(e))] for i in ids if (i, end_key(e)) in dd), (0, 0))
                vals += v
            if any(vals):
                r.append(vals); hits += 1
    db['dd'] = f'FAA NASR declared distances, cycle effective {cyc:%Y-%m-%d}'
    print(hits, 'runways updated')
    print('KSPG:', A.get('KSPG'))
    if hits < 100:
        sys.exit('Suspiciously few matches; not writing.')
    open('runways.json', 'w').write(json.dumps(db, separators=(',', ':')))

    sw = open('sw.js').read()
    sw = re.sub(r"VERSION='([^']*?-v\d+)[^']*'", lambda m: f"VERSION='{m.group(1)}-dd{cyc:%Y%m%d}'", sw, count=1)
    open('sw.js', 'w').write(sw)


main()
