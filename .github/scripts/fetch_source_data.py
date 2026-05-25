# .github/scripts/fetch_source_data.py
"""
GitHub Action 脚本：
1. Playwright 访问 zoomeye.ai API URL（自动过加速乐）
2. 从页面提取 JSON 数据
3. 清洗后 POST 回 HF Spaces
"""
import os
import asyncio
import json
from playwright.async_api import async_playwright
import aiohttp

from urllib.parse import urlparse

SOURCE_URL = os.getenv("SOURCE_URL", "")
SOURCE_TYPE = os.getenv("SOURCE_TYPE", "zoomeye")
CALLBACK_URL = os.getenv("CALLBACK_URL", "")
CALLBACK_TOKEN = os.getenv("CALLBACK_TOKEN", "")


async def fetch_via_playwright(api_url: str, home_url: str) -> dict:
    """Playwright 过加速乐后获取 API 数据"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # 1. 先过首页 JSL 挑战，拿到 cookie
        print(f"[步骤1] 访问 {home_url} 过 JSL 挑战...")
        await page.goto(home_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)

        # 2. 同一浏览器上下文访问 API URL
        print("[步骤2] 携带 cookie 访问 API...")
        resp = await page.goto(api_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            body_text = await page.evaluate("() => document.body.innerText")
            await browser.close()
            return json.loads(body_text)
        else:
            # 可能仍是 HTML 挑战页，再等一会儿重试
            print(f"[警告] 响应类型: {content_type}，等待后重试...")
            await page.wait_for_timeout(5000)
            resp2 = await page.reload(wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            body_text = await page.evaluate("() => document.body.innerText")
            await browser.close()
            return json.loads(body_text)


def clean_zoomeye_matches(matches):
    """zoomeye 返回格式清洗为统一格式"""
    sources = []
    for item in matches:
        ip = item.get("ip", "")
        portinfo = item.get("portinfo", {})
        port = portinfo.get("port", "")
        if not port:
            port = item.get("port", "")
        if ip and port:
            geo = item.get("geoinfo", {})
            sources.append({
                "host": f"{ip}:{port}",
                "geoRegion": geo.get("subdivisions", {}).get("names", {}).get("cn", ""),
                "geoOperator": geo.get("organization", "")
            })
    return sources


async def main():
    if not SOURCE_URL or not CALLBACK_URL:
        print("[ERROR] 缺少 SOURCE_URL 或 CALLBACK_URL 环境变量")
        return

    # 从 SOURCE_URL 解析出首页 URL
    parsed = urlparse(SOURCE_URL)
    home_url = f"{parsed.scheme}://{parsed.netloc}/"

    print(f"[开始] source_url={SOURCE_URL}, source_type={SOURCE_TYPE}")

    # 1. Playwright 过 JSL 挑战后获取数据
    print("[步骤1] Playwright 获取数据...")
    try:
        data = await fetch_via_playwright(SOURCE_URL, home_url)
        matches = data.get("matches", [])
        total = data.get("total", 0)
        print(f"  → 本页 {len(matches)} 条 (总计 {total})")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return

    sources = clean_zoomeye_matches(matches)

    # 2. 去重
    seen = set()
    unique_sources = []
    for s in sources:
        if s["host"] not in seen:
            seen.add(s["host"])
            unique_sources.append(s)

    print(f"[去重后] {len(unique_sources)} 个唯一 host")

    # 3. POST 回 HF Spaces
    print(f"[步骤2] 推送数据到 {CALLBACK_URL}")
    async with aiohttp.ClientSession() as session:
        headers = {"Content-Type": "application/json"}
        if CALLBACK_TOKEN:
            headers["X-Callback-Token"] = CALLBACK_TOKEN

        payload = {
            "sourceType": SOURCE_TYPE,
            "hosts": unique_sources
        }

        async with session.post(
            CALLBACK_URL,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            body = await resp.text()
            print(f"[回调结果] status={resp.status}, body={body}")


asyncio.run(main())
