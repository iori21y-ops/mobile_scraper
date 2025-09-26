import os, json, asyncio, time
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

TARGETS = [u.strip() for u in os.environ.get("TARGET_URLS", "https://auto.danawa.com/news/").split(",") if u.strip()]
CSS_ITEM  = os.environ.get("CSS_ITEM",  "li")           # 목록 아이템 선택자
CSS_TITLE = os.environ.get("CSS_TITLE", "a")            # 아이템 내부 제목 선택자
CSS_LINK  = os.environ.get("CSS_LINK",  "a")            # 아이템 내부 링크 선택자
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "10"))

async def scrape_url(pw, url: str):
    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page()
    # 한국 사이트 우호 헤더
    await page.set_extra_http_headers({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9"
    })
    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    # JS 렌더링 요소가 있으면 조금 더 대기
    await page.wait_for_timeout(1200)
    html = await page.content()

    # 👉 HTML 저장 (디버깅/셀렉터 확인용)
    safe_name = url.replace("https://", "").replace("/", "_")
    dump_path = f"data/{safe_name}.html"
    os.makedirs("data", exist_ok=True)
    with open(dump_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[DEBUG] Saved HTML snapshot: {dump_path}")

    await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    out = []
    for li in soup.select(CSS_ITEM)[:MAX_ITEMS]:
        # 제목
        t_el = li.select_one(CSS_TITLE)
        title = (t_el.get_text(strip=True) if t_el else None)
        # 링크
        a_el = li.select_one(CSS_LINK)
        href = a_el.get("href") if a_el else None
        if href and href.startswith("//"):
            href = "https:" + href
        out.append({"title": title, "url": href})
    return out

async def main_async():
    data = []
    async with async_playwright() as pw:
        for u in TARGETS:
            try:
                items = await scrape_url(pw, u)
                data.append({"source": u, "items": items})
                time.sleep(1)
            except Exception as e:
                data.append({"source": u, "error": str(e)})

    payload = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "count_sources": len(TARGETS),
        "results": data,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/results.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(main_async())