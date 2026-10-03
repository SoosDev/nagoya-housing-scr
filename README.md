# Nagoya Housing

Weekly-refreshed shortlist of for-sale homes in Nagoya (千種・東・昭和・瑞穂・名東・天白), screened for:

- ≤10 min walk to a station; used homes ≤25 years old
- 12 frequently cited 中学校学区 (matched against the city's official 通学区域 lists)
- Flood signals: 8 Sept 2026 heavy-rain damage, city hazard maps, GSI ground elevation
- Supermarkets and clinics near the station

## How it updates

`.github/workflows/weekly.yml` runs every Monday 06:13 JST:

1. `scripts/scrape.py` reads SUUMO list pages into `data/listings_raw.json`. If scraping fails or returns too few rows, the previous data is kept.
2. `scripts/build.py` joins school districts, flood rules and elevation (cached in `data/cache/geo.csv`; only new addresses are looked up), tracks first-seen dates, and renders `_site/index.html`.
3. The data is committed and the site is deployed to GitHub Pages.

Run it manually from the Actions tab with **Run workflow**.

## Editing criteria

- Wards, walk/age limits, target school districts: `scripts/config.py`
- Flood avoid/caution towns and thresholds: `data/static/flood_rules.json`
- Page layout: `site/template.html`

## Caveats

"No flag found" is not a flood clearance; check each address on the [city hazard map](https://www.city.nagoya.jp/bousaiportal/hazardmap/1036428.html) or [重ねるハザードマップ](https://disaportal.gsi.go.jp/). School districts come from real-estate sources; Nagoya publishes no official ranking. Prices come from SUUMO list pages.
