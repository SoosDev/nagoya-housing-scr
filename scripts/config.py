"""Search settings. Edit here to change what the weekly run collects."""

WARDS = {
    # ward name: SUUMO URL slug
    "千種区": "nagoyashichikusa",
    "東区": "nagoyashihigashi",
    "昭和区": "nagoyashishowa",
    "瑞穂区": "nagoyashimizuho",
    "名東区": "nagoyashimeito",
    "天白区": "nagoyashitempaku",
}

MAX_WALK_MIN = 10        # minutes to nearest station
MAX_AGE_YEARS = 25       # for used properties

# Junior high school districts shown on the site (frequently cited as strong).
TARGET_JH = [
    "城山中", "冨士中", "汐路中", "川名中", "神丘中", "東星中",
    "桜山中", "猪高中", "萩山中", "千種台中", "高針台中", "御幸山中",
]

# SUUMO list pages per property type. {slug} and {page} are filled in.
SOURCES = {
    "中古マンション": "https://suumo.jp/ms/chuko/aichi/sc_{slug}/?cn=25&et=10&page={page}",
    "中古一戸建て": "https://suumo.jp/chukoikkodate/aichi/sc_{slug}/?cn=25&et=10&pc=50&page={page}",
    "新築一戸建て": "https://suumo.jp/ikkodate/aichi/sc_{slug}/?et=10&pc=50&page={page}",
    "新築マンション": "https://suumo.jp/ms/shinchiku/aichi/sc_{slug}/?page={page}",
}

REQUEST_DELAY_S = 2.5    # polite pause between SUUMO requests
USER_AGENT = "Mozilla/5.0 (compatible; nagoya-housing-weekly/1.0; personal home search)"
