"""Scrape SUUMO for-sale list pages into data/listings_raw.json.

Only list pages are fetched (no detail pages, nothing under /jj/, which robots.txt disallows).
"""
import json, re, sys, time, unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
import config

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "listings_raw.json"
session = requests.Session()
session.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ja"})


def nk(s):
    return unicodedata.normalize("NFKC", s or "").strip()


def get(url, tries=3):
    for i in range(tries):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except requests.RequestException as e:
            print(f"  retry {i + 1} {url}: {e}", file=sys.stderr)
            time.sleep(10 * (i + 1))
    raise RuntimeError(f"failed: {url}")


def parse_price(s):
    s = nk(s)
    if not s or "未定" in s:
        return None
    m = re.search(r"(?:(\d+)億)?\s*(\d+(?:\.\d+)?)?万", s)
    if m and (m.group(1) or m.group(2)):
        return int(m.group(1) or 0) * 10000 + float(m.group(2) or 0)
    m = re.search(r"(\d+)億円", s)
    return int(m.group(1)) * 10000 if m else None


def parse_walk(s):
    nums = [int(x) for x in re.findall(r"徒歩\s*(\d+)\s*分", nk(s))]
    return min(nums) if nums else None


def parse_station(s):
    s = nk(s)
    m = re.search(r"「([^」]+)」", s) or re.search(r"/\s*([^\s/]+?)\s*(?:徒歩|バス|$)", s)
    return m.group(1) if m else ""


def parse_year(s):
    m = re.search(r"(\d{4})年(?:(\d{1,2})月)?", nk(s))
    if not m:
        return None, ""
    return int(m.group(1)), f"{m.group(1)}-{int(m.group(2)):02d}" if m.group(2) else m.group(1)


def units_standard(soup):
    for u in soup.select(".property_unit"):
        if "cassette" in (u.get("class") or []):
            continue
        a = u.select_one("h2 a")
        f = {}
        for dl in u.select("dl"):
            dt, dd = dl.find("dt"), dl.find("dd")
            if dt and dd:
                f[nk(dt.get_text())] = nk(dd.get_text(" "))
        yield a, f


def units_cassette(soup):
    for u in soup.select(".cassette.property_unit"):
        a = u.select_one("h2 a")
        f = {"物件名": nk(a.get_text()) if a else ""}
        for it in u.select(".cassette_basic-item"):
            t, v = it.select_one(".cassette_basic-title"), it.select_one(".cassette_basic-value")
            if t and v:
                f[nk(t.get_text())] = nk(v.get_text(" "))
        p = u.select_one(".cassette_price-value")
        d = u.select_one(".cassette_price-description")
        f["販売価格"] = nk(p.get_text(" ")) if p else ""
        if d:
            parts = [x.strip() for x in nk(d.get_text(" ")).split("/")]
            f["間取り"] = parts[0] if parts else ""
            f["専有面積"] = parts[1] if len(parts) > 1 else ""
        yield a, f


def to_row(ptype, ward, a, f, base):
    if not a:
        return None
    url = urljoin(base, a.get("href", "").split("?")[0])
    layout = f.get("間取り", "")
    area = f.get("専有面積") or f.get("建物面積", "")
    if ptype == "新築一戸建て" and not (layout or f.get("建物面積")):
        return None  # land-only listing mixed into results
    built_text = f.get("築年月") or f.get("完成時期(築年月)") or f.get("引渡時期") or f.get("完成時期") or ""
    by, built = parse_year(built_text)
    station_text = f.get("沿線・駅") or f.get("交通", "")
    price_text = f.get("販売価格", "")
    return {
        "type": ptype, "ward": ward,
        "name": f.get("物件名") or nk(a.get_text()),
        "price_man_yen": parse_price(price_text), "price_text": price_text,
        "layout": layout,
        "area_m2": re.sub(r"m\s*2|㎡|\(.*?\)|（.*?）", "", area).strip(),
        "land_m2": re.sub(r"m\s*2|㎡|\(.*?\)|（.*?）", "", f.get("土地面積", "")).strip(),
        "built": built or built_text, "built_year": by,
        "address": f.get("所在地", "").replace("愛知県", ""),
        "station": parse_station(station_text), "walk_min": parse_walk(station_text),
        "url": url,
    }


def scrape():
    rows, seen = [], set()
    this_year = date.today().year
    for ptype, tmpl in config.SOURCES.items():
        for ward, slug in config.WARDS.items():
            page, got = 1, 0
            while page <= 60:
                url = tmpl.format(slug=slug, page=page)
                html = get(url)
                time.sleep(config.REQUEST_DELAY_S)
                if not html:
                    break
                soup = BeautifulSoup(html, "html.parser")
                gen = units_cassette(soup) if ptype == "新築マンション" else units_standard(soup)
                new = 0
                for a, f in gen:
                    r = to_row(ptype, ward, a, f, url)
                    if not r or r["url"] in seen:
                        continue
                    seen.add(r["url"])
                    new += 1
                    if r["walk_min"] is None or r["walk_min"] > config.MAX_WALK_MIN:
                        continue
                    if ptype.startswith("中古") and r["built_year"] and r["built_year"] < this_year - config.MAX_AGE_YEARS:
                        continue
                    rows.append(r)
                    got += 1
                if new == 0:
                    break
                page += 1
            print(f"{ptype} {ward}: {got}")
    if len(rows) < 100:
        raise SystemExit(f"Only {len(rows)} listings scraped; SUUMO layout may have changed or access is blocked. Keeping last data.")
    OUT.write_text(json.dumps({"scraped": date.today().isoformat(), "rows": rows}, ensure_ascii=False, indent=0))
    print(f"total {len(rows)} -> {OUT}")


if __name__ == "__main__":
    scrape()
