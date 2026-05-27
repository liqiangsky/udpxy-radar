# .github/scripts/fetch_source_data.py
"""
通用 GitHub Action 脚本：
1. Playwright 访问目标 URL（自动过加速乐）
2. 从页面提取 JSON 数据
3. 按 source_type 加载对应清洗器清洗数据
4. POST 回 HF Spaces 回调接口
"""
import os
import sys
import json
import importlib
import asyncio
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import aiohttp

SOURCE_URL = os.getenv("SOURCE_URL", "")
SOURCE_TYPE = os.getenv("SOURCE_TYPE", "")
CALLBACK_URL = os.getenv("CALLBACK_URL", "")
CALLBACK_TOKEN = os.getenv("CALLBACK_TOKEN", "")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


async def fetch_via_playwright(api_url: str, home_url: str) -> dict:
    """通过 Playwright 访问目标 URL 获取 JSON 数据（支持过 JS 挑战页）"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # 1. 先访问首页过 JS 挑战，建立会话 cookie
        print(f"[步骤1] 访问 {home_url} 建立会话...")
        await page.goto(home_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)

        # 2. 同一浏览器上下文访问目标 URL
        print("[步骤2] 获取目标数据...")
        resp = await page.goto(api_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            body_text = await page.evaluate("() => document.body.innerText")
            await browser.close()
            return json.loads(body_text)
        else:
            # 可能仍是挑战页，等待后刷新重试
            print(f"[警告] 响应类型: {content_type}，等待后重试...")
            await page.wait_for_timeout(5000)
            resp2 = await page.reload(wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            body_text = await page.evaluate("() => document.body.innerText")
            await browser.close()
            return json.loads(body_text)


def load_cleaner(source_type: str):
    """按 source_type 动态加载 cleaners 目录下的对应清洗器模块
    约定: cleaners/{source_type}_cleaner.py 必须实现 clean(data: dict) -> list[dict]
    """
    cleaner_name = f"{source_type}_cleaner"
    cleaners_dir = os.path.join(SCRIPT_DIR, "cleaners")

    if cleaner_name not in sys.modules:
        # 确保 cleaners 目录在 sys.path 中
        if cleaners_dir not in sys.path:
            sys.path.insert(0, cleaners_dir)
        try:
            mod = importlib.import_module(cleaner_name)
            sys.modules[cleaner_name] = mod
        except ImportError:
            return None

    mod = sys.modules[cleaner_name]
    if hasattr(mod, "clean") and callable(mod.clean):
        return mod.clean
    return None


async def main():
    if not SOURCE_URL or not CALLBACK_URL:
        print("[ERROR] 缺少 SOURCE_URL 或 CALLBACK_URL 环境变量")
        return

    print(f"[开始] source_url={SOURCE_URL}, source_type={SOURCE_TYPE}")

    # 使用 Playwright 过 JS 挑战
    parsed = urlparse(SOURCE_URL)
    home_url = f"{parsed.scheme}://{parsed.netloc}/"

    # 1. Playwright 获取数据
    print("[步骤1] Playwright 获取数据...")
    try:
        data = await fetch_via_playwright(SOURCE_URL, home_url)
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return

    # 2. 加载数据清洗器
    cleaner = load_cleaner(SOURCE_TYPE)
    if cleaner:
        print(f"[步骤2] 使用清洗器: {SOURCE_TYPE}_cleaner")
        sources = cleaner(data)
    else:
        print(f"[警告] 未找到清洗器 {SOURCE_TYPE}_cleaner，尝试通用解析")
        sources = []
        for key in ("matches", "hosts", "data_list", "data"):
            if key in data and isinstance(data[key], list):
                sources = [{"host": item} if isinstance(item, str) else item for item in data[key]]
                print(f"  → 通用解析: 从 '{key}' 字段提取 {len(sources)} 条")
                break
        else:
            print(f"❌ 无法解析响应数据，请为 {SOURCE_TYPE} 编写清洗器")
            return

    print(f"  → 清洗后 {len(sources)} 条数据")

    # 3. 按 host 去重
    seen = set()
    unique_sources = []
    for s in sources:
        host = s.get("host", "")
        if host and host not in seen:
            seen.add(host)
            unique_sources.append(s)

    print(f"[去重后] {len(unique_sources)} 个唯一 host")

    # 4. POST 回调推送数据
    print(f"[步骤3] 推送数据到 {CALLBACK_URL}")
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
