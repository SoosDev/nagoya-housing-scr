"""Join scraped listings with school districts, flood rules, elevation and station amenities,
then render site/index.html into _site/.
"""
import json, re, sys, time, unicodedata
from datetime import date
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
import config

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
OUT_DIR = ROOT / "_site"
KAN = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}


def nz(s):
    return unicodedata.normalize('NFKC', str(s)).replace('彌', '弥').replace('ヶ', 'ケ')


def kan2int(s):
    s = nz(s)
    if s.isdigit():
        return int(s)
    if s == '十':
        return 10
    if s.startswith('十'):
        return 10 + KAN[s[1]]
    if len(s) == 2 and s[1] == '十':
        return KAN[s[0]] * 10
    return KAN.get(s)


def parse_chome(c):
    if not isinstance(c, str) or '丁目' not in c:
        return None
    out = set()
    for part in re.split('[・、,]', nz(c).replace('丁目', '')):
        m = re.match(r'^(\S+?)[～~\-](\S+)$', part.strip())
        try:
            if m:
                out |= set(range(kan2int(m.group(1)), kan2int(m.group(2)) + 1))
            else:
                out.add(kan2int(part.strip()))
        except Exception:
            return None
    out.discard(None)
    return out or None


def parse_addr(a):
    a = nz(a).replace('愛知県', '').replace('名古屋市', '')
    m = re.match(r'^(\S+?区)(.*)$', a)
    if not m:
        return None, None, None
    ward, rest = m.group(1), re.split(r'[\s(（]', m.group(2))[0]
    m2 = re.match(r'^(\D+?)(\d+)', rest)
    if m2:
        return ward, m2.group(1).replace('丁目', ''), int(m2.group(2))
    return ward, rest, None


GAKKU = pd.read_csv(D / 'static' / 'gakku.csv', encoding='utf-8-sig')
GAKKU['chome_set'] = GAKKU['chome'].apply(parse_chome)
GAKKU['town_n'] = GAKKU['town'].apply(nz)


def lookup_school(ward, town, ch):
    if not ward or not town:
        return '', ''
    cand = GAKKU[GAKKU.ward == ward]
    hit = cand[cand.town_n == town]
    if hit.empty:
        hit = cand[cand.town_n.apply(lambda t: town.startswith(t) or t.startswith(town))]
    if hit.empty:
        return '', ''
    if ch is not None:
        h2 = hit[hit.chome_set.apply(lambda s: s is None or ch in s)]
        if not h2.empty:
            hit = h2
    r = hit.iloc[0]
    return r.elementary, r.junior_high


# ---------- elevation (GSI), cached ----------
GEO_PATH = D / 'cache' / 'geo.csv'
GEO = pd.read_csv(GEO_PATH) if GEO_PATH.exists() else pd.DataFrame(columns=['geo_q', 'lat', 'lon', 'elev_m', 'rel_m'])
GEO_IDX = {r.geo_q: r for r in GEO.itertuples()}
sess = requests.Session()
sess.headers['User-Agent'] = config.USER_AGENT


def _elev(lat, lon):
    r = sess.get('https://cyberjapandata2.gsi.go.jp/general/dem/scripts/getelevation.php',
                 params={'lon': lon, 'lat': lat, 'outtype': 'JSON'}, timeout=20)
    time.sleep(1.0)
    v = r.json().get('elevation')
    return float(v) if v not in (None, '-----') else None


def geo_lookup(q, budget):
    if q in GEO_IDX:
        r = GEO_IDX[q]
        return r.elev_m, r.rel_m
    if budget[0] <= 0:
        return None, None
    budget[0] -= 1
    try:
        res = sess.get('https://msearch.gsi.go.jp/address-search/AddressSearch', params={'q': q}, timeout=20).json()
        time.sleep(1.0)
        if not res:
            raise ValueError('no match')
        lon, lat = res[0]['geometry']['coordinates']
        c = _elev(lat, lon)
        nb = [_elev(lat + dy, lon + dx) for dy, dx in ((0.0018, 0), (-0.0018, 0), (0, 0.0022), (0, -0.0022))]
        nb = [x for x in nb if x is not None]
        rel = round(c - sum(nb) / len(nb), 2) if c is not None and nb else None
    except Exception as e:
        print(f'  geo fail {q}: {e}')
        return None, None
    row = pd.DataFrame([{'geo_q': q, 'lat': lat, 'lon': lon, 'elev_m': c, 'rel_m': rel}])
    global GEO
    GEO = pd.concat([GEO, row], ignore_index=True)
    GEO_IDX[q] = next(row.itertuples())
    return c, rel


def main():
    raw = json.loads((D / 'listings_raw.json').read_text())
    rules = json.loads((D / 'static' / 'flood_rules.json').read_text())
    am = pd.read_csv(D / 'static' / 'amenities.csv').set_index('station')
    seen_path = D / 'first_seen.json'
    existed = seen_path.exists()
    seen = json.loads(seen_path.read_text()) if existed else {}
    today = date.today().isoformat()

    df = pd.DataFrame(raw['rows'])
    df['area_num'] = pd.to_numeric(df.area_m2.astype(str).str.extract(r'([\d.]+)')[0], errors='coerce')
    parsed = df.address.apply(parse_addr)
    df['ward'] = [p[0] or w for p, w in zip(parsed, df.ward)]
    df['town'] = [p[1] for p in parsed]
    df['chome_no'] = [p[2] for p in parsed]
    sch = [lookup_school(*p) for p in parsed]
    df['es'] = [s[0] for s in sch]
    df['jh'] = [s[1] for s in sch]
    df['tj'] = df.jh.apply(lambda s: '、'.join(t for t in config.TARGET_JH if isinstance(s, str) and t in s))
    df = df[df.tj != ''].copy()
    df['key'] = df.type + '|' + df.address + '|' + df.price_man_yen.astype(str) + '|' + df.area_num.round(0).astype(str)
    df = df.drop_duplicates('key')

    budget = [200]
    out = []
    for r in df.itertuples():
        ch = '' if r.chome_no is None or pd.isna(r.chome_no) or r.chome_no > 20 else f'{int(r.chome_no)}丁目'
        q = f'名古屋市{r.ward}{r.town}{ch}'
        e, rel = geo_lookup(q, budget)
        g = GEO_IDX.get(q)  # 丁目-level point for the map
        la, lo = (None, None) if g is None or pd.isna(g.lat) else (round(float(g.lat), 6), round(float(g.lon), 6))
        e = None if e is None or pd.isna(e) else float(e)
        rel = None if rel is None or pd.isna(rel) else float(rel)
        town = nz(r.town or '')
        av = rules['avoid'].get(r.ward, {})
        ca = rules['caution'].get(r.ward, {})
        hit_av = next((v for k, v in av.items() if town.startswith(nz(k))), None)
        hit_ca = next((v for k, v in ca.items() if town.startswith(nz(k))), None)
        reasons = []
        if hit_av:
            flag = 'Avoid'; reasons.append(hit_av)
        else:
            flag = 'No flag found'
            if hit_ca:
                flag = 'Caution'; reasons.append(hit_ca)
            if e is not None and e < rules['low_ground_m']:
                flag = 'Caution'; reasons.append(f'Low ground ({e:.0f} m); check river/storm-surge hazard map')
            if rel is not None and rel <= rules['local_low_spot_m']:
                flag = 'Caution'; reasons.append(f'Local low spot (≈{rel:.0f} m below surroundings)')
        a = am.loc[r.station] if r.station in am.index else None
        first = seen.setdefault(r.url, today if existed else 'initial')
        out.append(dict(
            t=r.type, n=str(r.name)[:60], p=r.price_man_yen, pt=r.price_text if r.price_man_yen is None else '',
            l=r.layout, a=r.area_m2, an=None if pd.isna(r.area_num) else r.area_num, ld=r.land_m2, b=r.built,
            by=None if r.built_year is None or pd.isna(r.built_year) else int(r.built_year),
            ad=r.address, w=r.ward, st=r.station, wk=r.walk_min, es=r.es, jh=r.jh, tj=r.tj,
            f=flag, fr='; '.join(reasons), e=e, rl=rel, wd=rules['ward_damage_2026_09'].get(r.ward),
            sm=None if a is None else int(a.supermarkets_n),
            sn='' if a is None or not isinstance(a.supermarkets_names, str) else re.split('[;、|]', a.supermarkets_names)[0].strip(),
            cl=None if a is None else int(a.clinics_n), pd=None if a is None else int(a.pediatric_n),
            u=r.url, fs=first, la=la, lo=lo))

    current = {o['u'] for o in out}
    seen = {k: v for k, v in seen.items() if k in current}
    seen_path.write_text(json.dumps(seen, ensure_ascii=False, indent=0))
    GEO.to_csv(GEO_PATH, index=False)
    (D / 'listings.json').write_text(json.dumps(out, ensure_ascii=False, indent=0, default=str))

    meta = dict(updated=raw['scraped'], total_scraped=len(raw['rows']), shown=len(out),
                new=sum(1 for o in out if o['fs'] == today))
    OUT_DIR.mkdir(exist_ok=True)
    tpl = (ROOT / 'site' / 'template.html').read_text()
    st = pd.read_csv(D / 'static' / 'stations.csv')
    stations = [[r.station, round(r.lat, 6), round(r.lng, 6)] for r in st.itertuples()]
    html = (tpl.replace('__DATA__', json.dumps(out, ensure_ascii=False, default=str))
              .replace('__META__', json.dumps(meta, ensure_ascii=False))
              .replace('__STATIONS__', json.dumps(stations, ensure_ascii=False)))
    (OUT_DIR / 'index.html').write_text(html)
    (OUT_DIR / '.nojekyll').write_text('')
    print(meta)


if __name__ == '__main__':
    main()
