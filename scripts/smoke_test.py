"""Read-only HTTP checks against a running Compose deployment (no dependencies)."""
import json
import sys
from urllib.request import urlopen

base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")


def fetch(path):
    with urlopen(base + path, timeout=15) as response:
        assert response.status == 200, (path, response.status)
        return response.read().decode("utf-8")


assert fetch("/healthz").strip() == "ok"
assert 'id="app"' in fetch("/")
assert 'id="app"' in fetch("/news/detail/1"), "SPA route fallback failed"
categories = json.loads(fetch("/api/news/categories"))
assert categories["code"] == 200 and categories["data"], categories
category_id = categories["data"][0]["id"]
news = json.loads(fetch(f"/api/news/list?categoryId={category_id}&page=1&pageSize=10"))
assert news["code"] == 200 and news["data"]["list"], news
print("PASS: frontend, health check, SPA route, API proxy, seeded database news")
