"""
Daily refresh script for the Beauty Trend Dashboard.

Reads NAVER_CLIENT_ID / NAVER_CLIENT_SECRET from environment variables
(set as GitHub Secrets in the Actions workflow), calls four Naver Open APIs,
embeds the result into templates/dashboard.html, and writes docs/index.html.

Local test:
    export NAVER_CLIENT_ID=...
    export NAVER_CLIENT_SECRET=...
    python scripts/refresh.py
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# ---------- Environment ----------
KST = timezone(timedelta(hours=9))
CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 필요합니다.",
          file=sys.stderr)
    sys.exit(1)

AUTH_HEADERS = {
    "X-Naver-Client-Id": CLIENT_ID,
    "X-Naver-Client-Secret": CLIENT_SECRET,
}

# ---------- Config (이 부분을 바꿔 다른 키워드/카테고리로 운영 가능) ----------
KEYWORD_GROUPS = [
    {"groupName": "뷰티",     "keywords": ["뷰티", "화장품"]},
    {"groupName": "스킨케어", "keywords": ["스킨케어", "에센스", "세럼"]},
    {"groupName": "메이크업", "keywords": ["메이크업", "쿠션", "립스틱"]},
]
SHOPPING_CATEGORIES = [
    {"name": "바디크림",   "param": ["50000281"]},
    {"name": "바디오일",   "param": ["50000282"]},
    {"name": "바디클렌저", "param": ["50000285"]},
]
SHOP_QUERY = "뷰티 화장품"
NEWS_QUERY = "뷰티 화장품 트렌드"
LOOKBACK_DAYS = 14
TOP_N_PRODUCTS = 10
TOP_N_NEWS = 8

# ---------- Naver API calls ----------
def datalab_search(start, end):
    body = {
        "startDate": start, "endDate": end, "timeUnit": "date",
        "keywordGroups": KEYWORD_GROUPS,
    }
    r = requests.post(
        "https://openapi.naver.com/v1/datalab/search",
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def datalab_shopping_category(start, end):
    body = {
        "startDate": start, "endDate": end, "timeUnit": "date",
        "category": SHOPPING_CATEGORIES,
    }
    r = requests.post(
        "https://openapi.naver.com/v1/datalab/shopping/categories",
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def search_shop(query, display):
    r = requests.get(
        "https://openapi.naver.com/v1/search/shop.json",
        headers=AUTH_HEADERS,
        params={"query": query, "display": display, "sort": "sim"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def search_news(query, display):
    r = requests.get(
        "https://openapi.naver.com/v1/search/news.json",
        headers=AUTH_HEADERS,
        params={"query": query, "display": display, "sort": "date"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

# ---------- Helpers ----------
_TAG_RE = re.compile(r"<[^>]+>")
_ENT = {"&quot;": '"', "&amp;": "&", "&lt;": "<", "&gt;": ">", "&#39;": "'"}

def clean(text):
    if not text:
        return ""
    text = _TAG_RE.sub("", text)
    for k, v in _ENT.items():
        text = text.replace(k, v)
    return text

# ---------- Main ----------
def main():
    today_kst = datetime.now(KST).date()
    # 네이버 데이터랩은 ~1일 지연 → 어제까지를 종료일로
    end = today_kst - timedelta(days=1)
    start = end - timedelta(days=LOOKBACK_DAYS - 1)
    period = {"start": start.isoformat(), "end": end.isoformat()}

    print(f"[fetch] {period['start']} ~ {period['end']}")

    search   = datalab_search(period["start"], period["end"])
    category = datalab_shopping_category(period["start"], period["end"])
    shop     = search_shop(SHOP_QUERY, TOP_N_PRODUCTS)
    news     = search_news(NEWS_QUERY, TOP_N_NEWS)

    products = [{
        "title":     clean(it.get("title", "")),
        "link":      it.get("link", ""),
        "image":     it.get("image", ""),
        "lprice":    it.get("lprice", ""),
        "mallName":  it.get("mallName", ""),
        "brand":     it.get("brand", ""),
        "maker":     it.get("maker", ""),
        "category2": it.get("category2", ""),
        "category3": it.get("category3", ""),
    } for it in shop.get("items", [])]

    news_items = [{
        "title":       clean(it.get("title", "")),
        "link":        it.get("link", ""),
        "pubDate":     it.get("pubDate", ""),
        "description": clean(it.get("description", "")),
    } for it in news.get("items", [])]

    snapshot = {
        "meta": {
            "fetchedAt": datetime.now(KST).isoformat(timespec="seconds"),
            "period":    period,
            "keywords":  SHOP_QUERY,
        },
        "search":   {"results": search.get("results", [])},
        "category": {"results": category.get("results", [])},
        "products": products,
        "news":     news_items,
    }

    root = Path(__file__).resolve().parent.parent
    template_path = root / "templates" / "dashboard.html"
    output_path = root / "docs" / "index.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html = template_path.read_text(encoding="utf-8")
    placeholder = "/* __SNAPSHOT_PLACEHOLDER__ */ null"
    if placeholder not in html:
        print("ERROR: 템플릿에서 placeholder를 찾지 못했습니다.", file=sys.stderr)
        sys.exit(2)
    snapshot_json = json.dumps(snapshot, ensure_ascii=False, indent=2)
    html = html.replace(placeholder, snapshot_json)

    output_path.write_text(html, encoding="utf-8")
    print(f"[write] {output_path.relative_to(root)} "
          f"({len(html):,} bytes)")
    print(f"  search   groups={len(snapshot['search']['results'])}")
    print(f"  category groups={len(snapshot['category']['results'])}")
    print(f"  products       ={len(snapshot['products'])}")
    print(f"  news           ={len(snapshot['news'])}")

if __name__ == "__main__":
    main()
