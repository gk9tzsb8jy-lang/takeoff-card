"""Build runways.json for the takeoff card.

US airports (including Puerto Rico and the USVI) come entirely from the FAA's
28-day NASR airport data: names, elevations, runway lengths, true headings,
displaced thresholds and declared distances (TORA/ASDA/LDA). Airports outside
the US come from OurAirports (public domain).

Run weekly by .github/workflows/faa-declared-distances.yml. It writes
tools/build-report.txt every time, and only replaces runways.json when the
result passes its sanity checks.

Testing: build_db.py <APT_CSV.zip> <airports.csv> <runways.csv>
"""
import csv, datetime as dt, io, json, math, re, sys, urllib.request, zipfile

UA = {'User-Agent': 'takeoff-card (github.com/gk9tzsb8jy-lang/takeoff-card)'}
EPOCH = dt.date(2025, 1, 23)  # a known AIRAC / NASR effective date
MIN_LEN = 2800
OA = 'https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/'
# OurAirports countries kept (US, PR and VI come from the FAA instead)
OA_C = set('CA MX BS CU JM KY TC DO HT BZ GT HN SV NI CR PA AW CW BQ SX BB TT AG KN LC VC GD DM MQ GP VG AI MS BM BL MF'.split())
OA_HARD = ('ASP', 'CON', 'PEM', 'BIT', 'TAR', 'PAV', 'MAC', 'PSP')
FAA_HARD = ('ASPH', 'CONC', 'PEM', 'BITU', 'PSP', 'TRTD')
REPORT = []


def log(*a):
    s = ' '.join(str(x) for x in a); print(s); REPORT.append(s)


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        return r.read()


def cycles():
    n = (dt.date.today() - EPOCH).days // 28
    return [EPOCH + dt.timedelta(days=28 * k) for k in (n, n - 1)]


def download_faa():
    for d in cycles():
        url = f"https://nfdc.faa.gov/webContent/28DaySub/extra/{d:%d_%b_%Y}_APT_CSV.zip"
        try:
            log('trying', url); return d, get(url)
        except Exception as e:
            log('  no:', e)
    base = 'https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/'
    for d in cycles():
        try:
            page = get(f'{base}{d:%Y-%m-%d}').decode('utf-8', 'replace')
        except Exception as e:
            log('  page', d, e); continue
        m = re.search(r'https?://[^"\']+APT_CSV\.zip', page)
        if m:
            log('found', m.group(0)); return d, get(m.group(0))
    raise SystemExit('Could not find the FAA APT_CSV zip for the current or previous cycle.')


def table(z, suffix):
    name = next(n for n in z.namelist() if n.upper().endswith(suffix))
    rows = list(csv.DictReader(io.TextIOWrapper(z.open(name), 'latin-1')))
    log(f'{suffix}: {len(rows)} rows; columns: {list(rows[0].keys())}')
    return rows


def col(rows, *cands, need=True):
    h = list(rows[0].keys())
    for c in cands:
        if c in h: return c
    for c in cands:
        for x in h:
            if c in x: return x
    if need: raise SystemExit(f'No column like {cands}')
    return None


def num(s):
    try: return float(s)
    except (TypeError, ValueError): return None


def ival(s):
    v = num(s); return int(round(v)) if v is not None else 0


def brg(a1, o1, a2, o2):
    a1, o1, a2, o2 = map(math.radians, (a1, o1, a2, o2))
    y = math.sin(o2 - o1) * math.cos(a2)
    x = math.cos(a1) * math.sin(a2) - math.sin(a1) * math.cos(a2) * math.cos(o2 - o1)
    return round(math.degrees(math.atan2(y, x))) % 360


def ident_hdg(e):
    m = re.match(r'\d+', e or ''); return (int(m.group()) * 10) % 360 if m else None


def nice(name):
    return ' '.join(w.capitalize() for w in name.split())[:40]


def build_faa(blob):
    z = zipfile.ZipFile(io.BytesIO(blob))
    B, R, E = table(z, 'APT_BASE.CSV'), table(z, 'APT_RWY.CSV'), table(z, 'APT_RWY_END.CSV')
    b_site, b_id = col(B, 'SITE_NO'), col(B, 'ARPT_ID')
    b_type, b_name = col(B, 'SITE_TYPE_CODE'), col(B, 'ARPT_NAME')
    b_elev, b_icao = col(B, 'ELEV'), col(B, 'ICAO_ID', need=False)
    b_stat = col(B, 'ARPT_STATUS', need=False)
    r_site, r_id, r_len = col(R, 'SITE_NO'), col(R, 'RWY_ID'), col(R, 'RWY_LEN')
    r_wid, r_surf = col(R, 'RWY_WIDTH'), col(R, 'SURFACE_TYPE_CODE')
    e_site, e_rwy, e_end = col(E, 'SITE_NO'), col(E, 'RWY_ID'), col(E, 'RWY_END_ID')
    e_true, e_disp = col(E, 'TRUE_ALIGNMENT'), col(E, 'DISPLACED_THR_LEN')
    e_lat, e_lon = col(E, 'LAT_DECIMAL', need=False), col(E, 'LONG_DECIMAL', need=False)
    e_tora, e_asda, e_lda = col(E, 'TKOF_RUN_AVBL'), col(E, 'ACLT_STOP_DIST_AVBL', 'ACLT_STOP'), col(E, 'LNDG_DIST_AVBL', 'LNDG_DIST')
    log('site types:', dict(__import__('collections').Counter(r[b_type] for r in B).most_common(8)))
    if b_stat: log('status:', dict(__import__('collections').Counter(r[b_stat] for r in B).most_common(8)))
    log('surfaces:', dict(__import__('collections').Counter(r[r_surf] for r in R).most_common(25)))
    if B[0].get('EFF_DATE'): log('FAA effective date:', B[0]['EFF_DATE'])

    apt = {}
    for r in B:
        if r[b_type].strip().upper() not in ('A', 'AIRPORT'): continue
        if b_stat and r[b_stat].strip().upper() not in ('O', ''): continue
        apt[r[b_site]] = r
    ends = {}
    for r in E:
        ends[(r[e_site], r[e_rwy].strip().upper(), r[e_end].strip().upper())] = r

    A, X = {}, {}
    for r in R:
        a = apt.get(r[r_site]); L = num(r[r_len]); rid = r[r_id].strip().upper()
        if not a or not L or L < MIN_LEN or rid.startswith('H'): continue
        surf = r[r_surf].upper()
        if not any(h in surf for h in FAA_HARD): continue
        parts = rid.split('/')
        if len(parts) != 2: continue
        le, he = parts
        el, eh = ends.get((r[r_site], rid, le)), ends.get((r[r_site], rid, he))
        def hdg(e1, e2, ident, other):
            t = num(e1[e_true]) if e1 else None
            if t is not None: return int(round(t)) % 360
            if e_lat and e1 and e2:
                p = [num(e1[e_lat]), num(e1[e_lon]), num(e2[e_lat]), num(e2[e_lon])]
                if None not in p and p[0] != p[2]: return brg(*p)
            t2 = num(e2[e_true]) if e2 else None
            if t2 is not None: return int(round(t2 + 180)) % 360
            return ident_hdg(ident) or 0
        h1, h2 = hdg(el, eh, le, he) or 360, hdg(eh, el, he, le) or 360
        dd = [ival(el[e_tora]) if el else 0, ival(el[e_asda]) if el else 0,
              ival(eh[e_tora]) if eh else 0, ival(eh[e_asda]) if eh else 0,
              ival(el[e_lda]) if el else 0, ival(eh[e_lda]) if eh else 0]
        row = [le, he, int(L), ival(r[r_wid]), h1, h2, ival(el[e_disp]) if el else 0, ival(eh[e_disp]) if eh else 0]
        if any(dd): row.append(dd)
        fid = a[b_id].strip().upper(); icao = (a[b_icao].strip().upper() if b_icao else '')
        key = icao or fid
        if key not in A:
            A[key] = [nice(a[b_name]), ival(a[b_elev]), []]
            if fid != key: X[fid] = key
            if not icao and len(fid) == 3: X.setdefault('K' + fid, key)
        A[key][2].append(row)
    return A, X


def build_oa(apt_csv, rwy_csv, faa_keys, faa_alias):
    ap = {r['ident']: r for r in csv.DictReader(io.StringIO(apt_csv)) if r['iso_country'] in OA_C and r['type'] in ('small_airport', 'medium_airport', 'large_airport')}
    A, X = {}, {}
    for r in csv.DictReader(io.StringIO(rwy_csv)):
        a = ap.get(r['airport_ident']); L = num(r['length_ft'])
        if not a or r['closed'] == '1' or not L or L < MIN_LEN or not any(h in r['surface'].upper() for h in OA_HARD): continue
        def hd(end, other):
            h = num(r[end + '_heading_degT'])
            if h is not None: return int(round(h)) % 360
            p = [num(r[k]) for k in (end + '_latitude_deg', end + '_longitude_deg', other + '_latitude_deg', other + '_longitude_deg')]
            if None not in p and p[0] != p[2]: return brg(*p)
            return ident_hdg(r[end + '_ident']) or 0
        A.setdefault(a['ident'], [a['name'][:40], ival(a['elevation_ft']), []])[2].append(
            [r['le_ident'], r['he_ident'], int(L), ival(r['width_ft']), hd('le', 'he') or 360, hd('he', 'le') or 360,
             ival(r['le_displaced_threshold_ft']), ival(r['he_displaced_threshold_ft'])])
    # Prefer the current 4-letter code when OurAirports keeps an old ident
    for k in list(A):
        g = ap[k]['gps_code'].strip().upper()
        if g and g != k and re.fullmatch('[A-Z]{4}', g) and g not in A: A[g] = A.pop(k); X[k] = g
    for k, v in ap.items():
        key = X.get(k, k)
        if key not in A: continue
        for c in ('gps_code', 'icao_code', 'local_code', 'iata_code'):
            c = v[c].strip().upper()
            if c and c != key and c not in A and c not in faa_keys and c not in faa_alias: X.setdefault(c, key)
    # never let an outside-US entry shadow a US one
    for k in list(A):
        if k in faa_keys: A.pop(k)
    return A, X


def main():
    if len(sys.argv) > 3:
        cyc, blob = dt.date.today(), open(sys.argv[1], 'rb').read()
        apt_csv, rwy_csv = open(sys.argv[2], encoding='utf-8').read(), open(sys.argv[3], encoding='utf-8').read()
    else:
        cyc, blob = download_faa()
        apt_csv, rwy_csv = get(OA + 'airports.csv').decode('utf-8'), get(OA + 'runways.csv').decode('utf-8')
    FA, FX = build_faa(blob)
    OA_A, OA_X = build_oa(apt_csv, rwy_csv, set(FA), set(FX))
    A = {**OA_A, **FA}; X = {**OA_X, **FX}
    X = {k: v for k, v in X.items() if k not in A and v in A}
    n_dd = sum(1 for a in FA.values() for r in a[2] if len(r) > 8)
    log(f'FAA (US): {len(FA)} airports, {sum(len(a[2]) for a in FA.values())} runways, {n_dd} with declared distances')
    log(f'OurAirports (outside US): {len(OA_A)} airports')
    for k in ('KSPG', 'KTPA', 'KPIE', 'KDNA', 'KEYW', 'X26', 'TJSJ', 'MMUN', 'MYNN', 'CYYZ'):
        log(k, A.get(k) or ('alias -> ' + X[k] if k in X else 'MISSING'))
    db = {'a': A, 'x': X,
          'src': f'FAA NASR (US, cycle {cyc:%Y-%m-%d}) and OurAirports (outside US, {dt.date.today():%Y-%m-%d})',
          'dd': f'FAA NASR declared distances, cycle effective {cyc:%Y-%m-%d}', 'ddEff': f'{cyc:%Y-%m-%d}'}
    ok = len(FA) > 3000 and n_dd > 500 and 'KSPG' in A and len(OA_A) > 300
    log('sanity checks', 'PASSED' if ok else 'FAILED; runways.json left unchanged')
    open('tools/build-report.txt', 'w').write(f'Build {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%MZ}\n' + '\n'.join(REPORT) + '\n')
    if not ok: return
    open('runways.json', 'w').write(json.dumps(db, separators=(',', ':'), ensure_ascii=False))
    sw = open('sw.js').read()
    sw = re.sub(r"VERSION='([^']*?-v\d+)[^']*'", lambda m: f"VERSION='{m.group(1)}-dd{cyc:%Y%m%d}'", sw, count=1)
    open('sw.js', 'w').write(sw)


main()
