"""Hunter (奇安信) 数据源拉取服务"""
import http.client
import ssl
import json
import aiohttp
import logging
from typing import List
from datetime import date
from urllib.parse import urlencode
from db.database import get_setting

logger = logging.getLogger("udpxy_radar")

HUNTER_HOST = "hunter.qianxin.com"
HUNTER_PATH = "/openApi/search"
# 固定搜索词: header="Server: udpxy"&&ip.country=="中国"
HUNTER_QUERY = 'aGVhZGVyPSJTZXJ2ZXI6IHVkcHh5IiYmaXAuY291bnRyeT09IuS4reWbvSI'
HUNTER_PAGE_SIZE = 10  # 每次 10 条（1 条 1 积分）


def _hunter_request(api_key: str, page: int, today: str) -> dict | None:
    """
    使用 http.client（标准库）发送请求，TLS 指纹更接近浏览器，
    绕过知道创宇 WAF 对 aiohttp TLS 指纹的识别。
    """
    query_string = urlencode({
        "api-key": api_key,
        "search": HUNTER_QUERY,
        "page": page,
        "page_size": HUNTER_PAGE_SIZE,
        "is_web": 1,
        "start_time": today,
        "end_time": today
    })
    url = f"{HUNTER_PATH}?{query_string}"

    logger.info(f"📡 [Hunter] 拉取第 {page} 页...")
    logger.info(f"🔍 [Hunter] 完整 URL: https://{HUNTER_HOST}{url}")

    ctx = ssl.create_default_context()
    conn = http.client.HTTPSConnection(HUNTER_HOST, 443, context=ctx)

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    try:
        conn.request("GET", url, headers=headers)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")

        logger.info(f"🔍 [Hunter] 响应状态码: {resp.status}")
        logger.info(f"🔍 [Hunter] 响应头: {dict(resp.getheaders())}")

        if resp.status != 200:
            logger.warning(f"⚠️ [Hunter] 请求失败，状态码: {resp.status}, 响应体: {body[:500]}")
            conn.close()
            return None

        conn.close()
        return json.loads(body)

    except Exception as e:
        logger.error(f"❌ [Hunter] 第 {page} 页请求异常: {e}")
        conn.close()
        return None


async def fetch_hunter_sources() -> List[dict]:
    """
    循环分页请求 Hunter API，每次 10 条，直到积分用完或无数据。
    解析 ip+port 为 host，geo 信息全部走 geoip 查询。
    """
    api_key = get_setting("hunter_api_key", "")
    if not api_key:
        logger.warning("⚠️ [Hunter] API Key 未配置")
        return []

    today = date.today().isoformat()
    all_sources = []
    page = 1

    while True:
        result = _hunter_request(api_key, page, today)
        if result is None:
            break

        if result.get("code") != 200:
            logger.warning(f"⚠️ [Hunter] 返回错误: {result.get('message', 'unknown')}")
            break

        data = result.get("data", {})
        arr = data.get("arr", [])
        rest_quota = data.get("rest_quota", "")
        total = data.get("total", 0)

        if not arr:
            logger.info(f"📄 [Hunter] 第 {page} 页无数据，停止翻页")
            break

        for item in arr:
            ip = item.get("ip", "")
            port = item.get("port", "")
            if ip and port:
                all_sources.append({"host": f"{ip}:{port}"})

        logger.info(f"📄 [Hunter] 第 {page} 页 -> {len(arr)} 条 (累计 {len(all_sources)}/{total}), {rest_quota}")

        # 判断积分是否用完
        if "0" in rest_quota:
            logger.info(f"📄 [Hunter] 积分已用完，停止翻页")
            break

        page += 1

    # 全部走 geoip 查询
    if all_sources:
        from services.geoip import enrich_geo_batch
        async with aiohttp.ClientSession() as session:
            enriched = await enrich_geo_batch(session, all_sources)
            logger.info(f"📄 [Hunter] 总计获取 {len(enriched)} 条数据")
            return enriched
    return []
